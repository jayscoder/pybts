from stable_baselines3.common.off_policy_algorithm import OffPolicyAlgorithm

from stable_baselines3.common.utils import (
    configure_logger, TrainFreq
)
import typing
from collections import deque
import time
import warnings
from typing import Optional
import numpy as np
from stable_baselines3.common.buffers import ReplayBuffer
from stable_baselines3.common.noise import ActionNoise
from stable_baselines3.common.type_aliases import (
    RolloutReturn, TrainFreq,
)
from stable_baselines3.common.utils import should_collect_more_steps
from gymnasium import spaces
from rl.rlhandler import RLHandler


def bt_off_policy_setup_learn(
        self: OffPolicyAlgorithm,
        tb_log_name: str = 'run',
        reset_num_timesteps: bool = True,
        total_timesteps: int = 10000,
):
    replay_buffer = self.replay_buffer
    truncate_last_traj = (
            self.optimize_memory_usage
            and reset_num_timesteps
            and replay_buffer is not None
            and (replay_buffer.full or replay_buffer.pos > 0)
    )
    if truncate_last_traj:
        warnings.warn(
                "The last trajectory in the replay buffer will be truncated, "
                "see https://github.com/DLR-RM/stable-baselines3/issues/46."
                "You should use `reset_num_timesteps=False` or `optimize_memory_usage=False`"
                "to avoid that issue."
        )
        assert replay_buffer is not None  # for mypy
        # Go to the previous index
        pos = (replay_buffer.pos - 1) % replay_buffer.buffer_size
        replay_buffer.dones[pos] = True

    self.start_time = time.time_ns()

    if self.ep_info_buffer is None or reset_num_timesteps:
        # Initialize buffers if they don't exist, or reinitialize if resetting counters
        self.ep_info_buffer = deque(maxlen=self._stats_window_size)
        self.ep_success_buffer = deque(maxlen=self._stats_window_size)

    if self.action_noise is not None:
        self.action_noise.reset()

    if reset_num_timesteps:
        self.num_timesteps = 0
        self._episode_num = 0
    else:
        # Make sure training timesteps are ahead of the internal counter
        total_timesteps += self.num_timesteps
    self._total_timesteps = total_timesteps
    self._num_timesteps_at_start = self.num_timesteps

    # Avoid resetting the environment when calling ``.learn()`` consecutive times
    if reset_num_timesteps or self._last_obs is None:
        assert self.env is not None
        self._last_obs = self.env.reset()  # type: ignore[assignment]
        self._last_episode_starts = np.ones((self.env.num_envs,), dtype=bool)
        # Retrieve unnormalized observation for saving into the buffer
        if self._vec_normalize_env is not None:
            self._last_original_obs = self._vec_normalize_env.get_original_obs()

    # Configure logger's outputs if no logger was passed
    if not self._custom_logger:
        self._logger = configure_logger(self.verbose, self.tensorboard_log, tb_log_name, reset_num_timesteps)

    return total_timesteps


class OffPolicyRLHandler(RLHandler):
    def __init__(self, model: OffPolicyAlgorithm, log_interval: int = 0):
        self.model = model
        self.num_collected_steps = 0
        self.num_collected_episodes = 0
        self.log_interval = log_interval

    def reset(self):
        pass

    def predict(self):
        # Switch to eval mode (this affects batch norm / dropout)
        self.model.policy.set_training_mode(False)
        if self.model.use_sde and self.model.sde_sample_freq > 0 and self.num_collected_steps % self.model.sde_sample_freq == 0:
            # Sample a new noise matrix
            self.model.actor.reset_noise(1)

        # Select action randomly or according to policy
        actions, buffer_actions = self.model._sample_action(self.model.learning_starts, self.model.action_noise, 1)

        return actions[0], None, None

    def observe(self, actions: np.ndarray, rewards: float, new_obs: typing.Any, dones: bool, infos: dict,
                values=None, log_probs=None) -> bool:

        # 数据都从单个处理成批量的
        if isinstance(new_obs, dict):
            new_obs = new_obs.copy()
            for k in new_obs:
                new_obs[k] = np.expand_dims(new_obs[k], axis=0)
        else:
            new_obs = np.expand_dims(new_obs, axis=0)
        rewards = np.array([rewards])
        dones = np.array([dones])
        infos = [infos]

        if actions is None:
            self.model._last_obs = new_obs
            return False

        self.model.num_timesteps += 1

        self.num_collected_steps += 1

        # Retrieve reward and episode length if using Monitor wrapper
        self.model._update_info_buffer(infos, dones)

        unscaled_actions = actions  # 原始动作
        # 数值标准化 Rescale the action from [low, high] to [-1, 1]，方便强化学习模型进行训练
        if isinstance(self.model.action_space, spaces.Box):
            scaled_actions = self.model.policy.scale_action(unscaled_actions)

            # We store the scaled action in the buffer
            buffer_actions = scaled_actions
        else:
            # Discrete case, no need to normalize or clip
            buffer_actions = unscaled_actions

        # Store data in replay buffer (normalized action and unnormalized observation)
        self.model._store_transition(self.model.replay_buffer, buffer_actions, new_obs, rewards, dones,
                                     infos)  # type: ignore[arg-type]

        self.model._update_current_progress_remaining(self.model.num_timesteps, self.model._total_timesteps)

        # For DQN, check if the target network should be updated
        # and update the exploration schedule
        # For SAC/TD3, the update is dones as the same time as the gradient update
        # see https://github.com/hill-a/stable-baselines/issues/900
        self.model._on_step()

        for idx, done in enumerate(dones):
            if done:
                # Update stats
                self.num_collected_episodes += 1
                self.model._episode_num += 1

                if self.model.action_noise is not None:
                    self.model.action_noise.reset()

                # Log training infos
                if self.log_interval > 0 and self.model._episode_num % self.log_interval == 0:
                    self.model._dump_logs()

        should_train = not should_collect_more_steps(self.model.train_freq, self.num_collected_steps,
                                                     self.num_collected_episodes)

        return should_train

    def train(self):

        if self.model.num_timesteps > 0 and self.model.num_timesteps > self.model.learning_starts:
            # If no `gradient_steps` is specified,
            # do as many gradients steps as steps performed during the rollout
            gradient_steps = self.model.gradient_steps if self.model.gradient_steps >= 0 else self.num_collected_steps
            # Special case when the user passes `gradient_steps=0`
            if gradient_steps > 0:
                self.model.train(batch_size=self.model.batch_size, gradient_steps=gradient_steps)

        self.num_collected_steps = 0
        self.num_collected_episodes = 0

# def bt_off_policy_insert_reply_buffer(
#         self: OffPolicyAlgorithm,
#         replay_buffer: ReplayBuffer,
#         action, new_obs, reward, done, info,
#         log_interval: Optional[int] = None):
#     """
#     动作填充，将外部的一些经验填充进来
#     基于动作重复的原理
#     :return:
#     """
#     # 数据都从单个处理成批量的
#     if isinstance(new_obs, dict):
#         new_obs = new_obs.copy()
#         for k in new_obs:
#             new_obs[k] = np.expand_dims(new_obs[k], axis=0)
#     else:
#         new_obs = np.expand_dims(new_obs, axis=0)
#     reward = np.array([reward])
#     done = np.array([done])
#     info = [info]
#
#     self.num_timesteps += 1
#
#     # Retrieve reward and episode length if using Monitor wrapper
#     self._update_info_buffer(info, done)
#
#     unscaled_action = action  # 原始动作
#     # 数值标准化 Rescale the action from [low, high] to [-1, 1]，方便强化学习模型进行训练
#     if isinstance(self.action_space, spaces.Box):
#         scaled_action = self.policy.scale_action(unscaled_action)
#
#         # We store the scaled action in the buffer
#         buffer_action = scaled_action
#     else:
#         # Discrete case, no need to normalize or clip
#         buffer_action = unscaled_action
#
#     # Store data in replay buffer (normalized action and unnormalized observation)
#     self._store_transition(replay_buffer, buffer_action, new_obs, reward, done, info)  # type: ignore[arg-type]
#
#     self._update_current_progress_remaining(self.num_timesteps, self._total_timesteps)
#
#     # For DQN, check if the target network should be updated
#     # and update the exploration schedule
#     # For SAC/TD3, the update is dones as the same time as the gradient update
#     # see https://github.com/hill-a/stable-baselines/issues/900
#     self._on_step()
#
#     for idx, done in enumerate(done):
#         if done:
#             # Update stats
#             self._episode_num += 1
#
#             # Log training infos
#             if log_interval is not None and self._episode_num % log_interval == 0:
#                 self._dump_logs()


# def bt_off_policy_collect_rollouts(
#         self: OffPolicyAlgorithm,
#         train_freq: TrainFreq,
#         replay_buffer: ReplayBuffer,
#         action_noise: Optional[ActionNoise] = None,
#         learning_starts: int = 0,
#         log_interval: Optional[int] = None,
# ) -> typing.Generator:
#     # Switch to eval mode (this affects batch norm / dropout)
#     self.policy.set_training_mode(False)
#
#     num_collected_steps, num_collected_episodes = 0, 0
#     env_num_envs = 1
#     assert train_freq.frequency > 0, "Should at least collect one step or episode."
#
#     if self.use_sde:
#         self.actor.reset_noise(env_num_envs)
#
#     continue_training = True
#
#     while should_collect_more_steps(train_freq, num_collected_steps, num_collected_episodes):
#         if self.use_sde and self.sde_sample_freq > 0 and num_collected_steps % self.sde_sample_freq == 0:
#             # Sample a new noise matrix
#             self.actor.reset_noise(env_num_envs)
#
#         # Select action randomly or according to policy
#         actions, buffer_actions = self._sample_action(learning_starts, action_noise, env_num_envs)
#
#         # Rescale and perform action
#         new_obs, rewards, dones, infos = yield actions[0]
#
#         # print('train_freq', train_freq, 'num_collected_steps', num_collected_steps, 'num_collected_episodes',
#         #       num_collected_episodes)
#
#         # 数据都从单个处理成批量的
#         if isinstance(new_obs, dict):
#             new_obs = new_obs.copy()
#             for k in new_obs:
#                 new_obs[k] = np.expand_dims(new_obs[k], axis=0)
#         else:
#             new_obs = np.expand_dims(new_obs, axis=0)
#         rewards = np.array([rewards])
#         dones = np.array([dones])
#         infos = [infos]
#
#         self.num_timesteps += env_num_envs
#
#         num_collected_steps += 1
#
#         # Retrieve reward and episode length if using Monitor wrapper
#         self._update_info_buffer(infos, dones)
#
#         # Store data in replay buffer (normalized action and unnormalized observation)
#         self._store_transition(replay_buffer, buffer_actions, new_obs, rewards, dones, infos)  # type: ignore[arg-type]
#
#         self._update_current_progress_remaining(self.num_timesteps, self._total_timesteps)
#
#         # For DQN, check if the target network should be updated
#         # and update the exploration schedule
#         # For SAC/TD3, the update is dones as the same time as the gradient update
#         # see https://github.com/hill-a/stable-baselines/issues/900
#         self._on_step()
#
#         for idx, done in enumerate(dones):
#             if done:
#                 # Update stats
#                 num_collected_episodes += 1
#                 self._episode_num += 1
#
#                 if action_noise is not None:
#                     action_noise.reset()
#
#                 # Log training infos
#                 if log_interval is not None and self._episode_num % log_interval == 0:
#                     self._dump_logs()
#
#     rollout_return = RolloutReturn(num_collected_steps * env_num_envs, num_collected_episodes, continue_training)
#     # print('bt_off_policy_collect_rollouts', rollout_return)
#     yield rollout_return
