import numpy as np
import torch
from gymnasium import spaces
from stable_baselines3.common.on_policy_algorithm import OnPolicyAlgorithm
from stable_baselines3.common.utils import (
    safe_mean,
    configure_logger
)
from stable_baselines3.common.type_aliases import GymEnv, Schedule, TensorDict, TrainFreq, TrainFrequencyUnit
import typing
import torch as th
import time
from collections import deque
import sys
from typing import Union, Dict
from rl.rlhandler import RLHandler


def obs_as_tensor(obs: Union[np.ndarray, Dict[str, np.ndarray]], device: th.device) -> Union[th.Tensor, TensorDict]:
    """
    Moves the observation to the given device.
    为了兼容mps，数据值用float32来保存
    :param obs:
    :param device: PyTorch device
    :return: PyTorch tensor of the observation on a desired device.
    """
    dtype = th.float32 if device == 'mps' else th.float64

    if isinstance(obs, np.ndarray):
        return th.as_tensor(obs, device=device, dtype=dtype)
    elif isinstance(obs, dict):
        return { key: th.as_tensor(_obs, device=device, dtype=dtype) for (key, _obs) in obs.items() }
    else:
        raise Exception(f"Unrecognized type of observation {type(obs)}")


def bt_on_policy_setup_learn(
        self: OnPolicyAlgorithm,
        obs,
        tb_log_name: str = 'run',
        reset_num_timesteps: bool = True,
        total_timesteps: int = 10000,
):
    """
    Initialize different variables needed for training.

    :param total_timesteps: The total number of samples (env steps) to train on
    :param reset_num_timesteps: Whether to reset or not the ``num_timesteps`` attribute
    :param tb_log_name: the name of the run for tensorboard log
    :return: Total timesteps and callback(s)
    """
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
        self._last_obs = np.expand_dims(obs, axis=0)  # type: ignore[assignment]
        self._last_episode_starts = np.ones((1,), dtype=bool)
        # Retrieve unnormalized observation for saving into the buffer
        if self._vec_normalize_env is not None:
            self._last_original_obs = self._vec_normalize_env.get_original_obs()

    # Configure logger's outputs if no logger was passed
    if not self._custom_logger:
        self._logger = configure_logger(self.verbose, self.tensorboard_log, tb_log_name, reset_num_timesteps)

    return total_timesteps


def bt_on_policy_insert_reply_buffer(
        self: OnPolicyAlgorithm,
        action, new_obs, reward, done, info):
    """
    经验填充，基于动作重复的原理
    在线策略学习中的经验填充可能会导致策略不稳定
    :param self:
    :param action:
    :param new_obs:
    :param reward:
    :param done:
    :param info:
    :return:
    """
    with th.no_grad():
        # Convert to pytorch tensor or to TensorDict
        obs_tensor = obs_as_tensor(self._last_obs, self.device)
        _, values, log_probs = self.policy(obs_tensor)

    # 数据都从单个处理成批量的
    if isinstance(new_obs, dict):
        # 处理一下字典数据的情况
        new_obs = new_obs.copy()
        for k in new_obs:
            new_obs[k] = np.expand_dims(new_obs[k], axis=0)
    else:
        new_obs = np.expand_dims(new_obs, axis=0)
    reward = np.array([reward])
    done = np.array([done])
    info = [info]

    self.num_timesteps += 1

    # Give access to local variables
    # callback.update_locals(locals())
    # if not callback.on_step():
    #     return False

    self._update_info_buffer(info, done)

    if isinstance(self.action_space, spaces.Discrete):
        # Reshape in case of discrete action
        action = action.reshape(-1, 1)

    # Handle timeout by bootstraping with value function
    # see GitHub issue #633
    # 在环境因达到最大步数而非自然终止时，提供一个合理的未来价值估计，从而帮助学习算法更好地理解和学习到达该状态的长期影响。
    # 这种处理方式是对传统强化学习中的处理截断问题的一种常见实践。
    # 在没有这种处理时，算法可能会错误地认为达到步数限制是一种负面的结果，而实际上它仅仅是由环境的设定导致的。
    for idx, done in enumerate(done):
        if (
                done
                and info[idx].get("truncated", False)
        ):
            terminal_obs = obs_as_tensor(self._last_obs, self.device)
            with th.no_grad():
                terminal_value = self.policy.predict_values(terminal_obs)[0]  # type: ignore[arg-type]
            reward[idx] += self.gamma * terminal_value

    self.rollout_buffer.add(
            self._last_obs,  # type: ignore[arg-type]
            action,
            reward,
            self._last_episode_starts,  # type: ignore[arg-type]
            values,
            log_probs,
    )

    self._last_obs = new_obs  # type: ignore[assignment]
    self._last_episode_starts = done


class OnPolicyRLHandler(RLHandler):

    def __init__(self, model: OnPolicyAlgorithm, obs: np.ndarray = None, log_interval: int = 0):
        self.model = model
        self.data = []
        if obs is not None:
            self.model._last_obs = obs
        self.n_steps = 0
        self.log_interval = log_interval
        self.iteration = 0

    def reset(self):
        if self.n_steps > 0:
            self.iteration += 1
        self.n_steps = 0
        self.model.rollout_buffer.reset()

    def predict(self):
        """训练预测"""
        # Switch to eval mode (this affects batch norm / dropout)
        self.model.policy.set_training_mode(False)

        assert self.model._last_obs is not None
        if self.model.use_sde and self.model.sde_sample_freq > 0 and self.n_steps % self.model.sde_sample_freq == 0:
            # Sample a new noise matrix
            self.model.policy.reset_noise(1)

        with th.no_grad():
            # Convert to pytorch tensor or to TensorDict
            obs_tensor = obs_as_tensor(self.model._last_obs, self.model.device)
            actions, values, log_probs = self.model.policy(obs_tensor)

        actions = actions.cpu().numpy()

        # Rescale and perform action
        clipped_actions = actions

        if isinstance(self.model.action_space, spaces.Box):
            if self.model.policy.squash_output:
                # Unscale the actions to match env bounds
                # if they were previously squashed (scaled in [-1, 1])
                clipped_actions = self.model.policy.unscale_action(clipped_actions)
            else:
                # Otherwise, clip the actions to avoid out of bound error
                # as we are sampling from an unbounded Gaussian distribution
                clipped_actions = np.clip(actions, self.model.action_space.low, self.model.action_space.high)

        return clipped_actions[0], values, log_probs

    def observe(self, actions: np.ndarray, rewards: float, new_obs: typing.Any, dones: bool, infos: dict,
                values=None, log_probs=None) -> bool:
        """
        观测
        :param actions:
        :param rewards:
        :param new_obs:
        :param dones:
        :param infos:
        :param values:
        :param log_probs:
        :return: 缓存池是否满了，如果满了，就要开始训练了，下一次观测就会清空缓存池
        """
        # 数据都从单个处理成批量的
        if isinstance(new_obs, dict):
            # 处理一下字典数据的情况
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

        actions = np.expand_dims(actions, axis=0)
        self.model.policy.set_training_mode(False)
        if self.model.rollout_buffer.full:
            # 缓存满了，就清空
            self.reset()

        if values is None or log_probs is None:
            assert self.model._last_obs is not None
            with th.no_grad():
                # Convert to pytorch tensor or to TensorDict
                obs_tensor = obs_as_tensor(self.model._last_obs, self.model.device)
                _, values, log_probs = self.model.policy(obs_tensor)

        self.model.num_timesteps += 1

        # Give access to local variables
        # callback.update_locals(locals())
        # if not callback.on_step():
        #     return False

        self.model._update_info_buffer(infos, dones)
        self.n_steps += 1

        if isinstance(self.model.action_space, spaces.Discrete):
            # Reshape in case of discrete action
            actions = actions.reshape(-1, 1)

        # Handle timeout by bootstraping with value function
        # see GitHub issue #633
        # 在环境因达到最大步数而非自然终止时，提供一个合理的未来价值估计，从而帮助学习算法更好地理解和学习到达该状态的长期影响。
        # 这种处理方式是对传统强化学习中的处理截断问题的一种常见实践。
        # 在没有这种处理时，算法可能会错误地认为达到步数限制是一种负面的结果，而实际上它仅仅是由环境的设定导致的。
        for idx, done in enumerate(dones):
            if (
                    done
                    and infos[idx].get("truncated", False)
            ):
                terminal_obs = obs_as_tensor(self.model._last_obs, self.model.device)
                with th.no_grad():
                    terminal_value = self.model.policy.predict_values(terminal_obs)[0]  # type: ignore[arg-type]
                rewards[idx] += self.model.gamma * terminal_value

        self.model.rollout_buffer.add(
                self.model._last_obs,  # type: ignore[arg-type]
                actions,
                rewards,
                self.model._last_episode_starts,  # type: ignore[arg-type]
                values,
                log_probs,
        )
        # print(
        #         f'collector_{self.n_steps}: {n_steps} actions={actions.tolist()} rewards={rewards.tolist()} dones={dones.tolist()} values={values.tolist()}')

        self.model._last_obs = new_obs  # type: ignore[assignment]
        self.model._last_episode_starts = dones

        if self.model.rollout_buffer.full:
            with th.no_grad():
                # Compute value for the last timestep
                values = self.model.policy.predict_values(
                        obs_as_tensor(new_obs, self.model.device))  # type: ignore[arg-type]

            self.model.rollout_buffer.compute_returns_and_advantage(last_values=values, dones=dones)

        return self.model.rollout_buffer.full

    def train(self):
        print('执行训练')
        # Display training infos
        if self.log_interval > 0 and self.iteration % self.log_interval == 0:
            assert self.model.ep_info_buffer is not None
            time_elapsed = max((time.time_ns() - self.model.start_time) / 1e9, sys.float_info.epsilon)
            fps = int((self.model.num_timesteps - self.model._num_timesteps_at_start) / time_elapsed)
            self.model.logger.record("time/iterations", self.iteration, exclude="tensorboard")
            if len(self.model.ep_info_buffer) > 0 and len(self.model.ep_info_buffer[0]) > 0:
                self.model.logger.record("rollout/ep_rew_mean",
                                         safe_mean([ep_info["r"] for ep_info in self.model.ep_info_buffer]))
                self.model.logger.record("rollout/ep_len_mean",
                                         safe_mean([ep_info["l"] for ep_info in self.model.ep_info_buffer]))
            self.model.logger.record("time/fps", fps)
            self.model.logger.record("time/time_elapsed", int(time_elapsed), exclude="tensorboard")
            self.model.logger.record("time/total_timesteps", self.model.num_timesteps, exclude="tensorboard")
            self.model.logger.dump(step=self.model.num_timesteps)

        self.model.train()
        # 训练完成之后就清空缓存
        self.reset()

# def bt_on_policy_collect_rollouts(self: OnPolicyAlgorithm, last_obs) -> typing.Generator:
#     """
#     Collect rollouts from an OnPolicyAlgorithm
#     :param self:
#     :param last_obs: last observation
#
#     collector = bt_on_policy_collect_rollouts(model, last_obs)
#     action = next(collector)
#     obs, reward, terminated, truncated, info = env.step(action)
#     collector.send(obs, reward, terminated or truncated, info)
#     """
#     # Switch to eval mode (this affects batch norm / dropout)
#     self.policy.set_training_mode(False)
#     n_steps = 0
#     self.rollout_buffer.reset()
#     # Sample new weights for the state dependent exploration
#     if self.use_sde:
#         self.policy.reset_noise(1)
#
#     self._last_obs = np.expand_dims(last_obs, axis=0)
#
#     # callback.on_rollout_start()
#     while not self.rollout_buffer.full:
#         if self.use_sde and self.sde_sample_freq > 0 and n_steps % self.sde_sample_freq == 0:
#             # Sample a new noise matrix
#             self.policy.reset_noise(1)
#
#         with th.no_grad():
#             # Convert to pytorch tensor or to TensorDict
#             obs_tensor = obs_as_tensor(self._last_obs, self.device)
#             actions, values, log_probs = self.policy(obs_tensor)
#         actions = actions.cpu().numpy()
#
#         # Rescale and perform action
#         clipped_actions = actions
#
#         if isinstance(self.action_space, spaces.Box):
#             if self.policy.squash_output:
#                 # Unscale the actions to match env bounds
#                 # if they were previously squashed (scaled in [-1, 1])
#                 clipped_actions = self.policy.unscale_action(clipped_actions)
#             else:
#                 # Otherwise, clip the actions to avoid out of bound error
#                 # as we are sampling from an unbounded Gaussian distribution
#                 clipped_actions = np.clip(actions, self.action_space.low, self.action_space.high)
#
#         new_obs, rewards, dones, infos = yield clipped_actions[0]
#
#         # 数据都从单个处理成批量的
#         if isinstance(new_obs, dict):
#             # 处理一下字典数据的情况
#             new_obs = new_obs.copy()
#             for k in new_obs:
#                 new_obs[k] = np.expand_dims(new_obs[k], axis=0)
#         else:
#             new_obs = np.expand_dims(new_obs, axis=0)
#         rewards = np.array([rewards])
#         dones = np.array([dones])
#         infos = [infos]
#
#         self.num_timesteps += 1
#
#         # Give access to local variables
#         # callback.update_locals(locals())
#         # if not callback.on_step():
#         #     return False
#
#         self._update_info_buffer(infos, dones)
#         n_steps += 1
#
#         if isinstance(self.action_space, spaces.Discrete):
#             # Reshape in case of discrete action
#             actions = actions.reshape(-1, 1)
#
#         # Handle timeout by bootstraping with value function
#         # see GitHub issue #633
#         # 在环境因达到最大步数而非自然终止时，提供一个合理的未来价值估计，从而帮助学习算法更好地理解和学习到达该状态的长期影响。
#         # 这种处理方式是对传统强化学习中的处理截断问题的一种常见实践。
#         # 在没有这种处理时，算法可能会错误地认为达到步数限制是一种负面的结果，而实际上它仅仅是由环境的设定导致的。
#         for idx, done in enumerate(dones):
#             if (
#                     done
#                     and infos[idx].get("truncated", False)
#             ):
#                 terminal_obs = obs_as_tensor(self._last_obs, self.device)
#                 with th.no_grad():
#                     terminal_value = self.policy.predict_values(terminal_obs)[0]  # type: ignore[arg-type]
#                 rewards[idx] += self.gamma * terminal_value
#
#         self.rollout_buffer.add(
#                 self._last_obs,  # type: ignore[arg-type]
#                 actions,
#                 rewards,
#                 self._last_episode_starts,  # type: ignore[arg-type]
#                 values,
#                 log_probs,
#         )
#         # print(
#         #         f'collector_{self.n_steps}: {n_steps} actions={actions.tolist()} rewards={rewards.tolist()} dones={dones.tolist()} values={values.tolist()}')
#
#         self._last_obs = new_obs  # type: ignore[assignment]
#         self._last_episode_starts = dones
#
#     with th.no_grad():
#         # Compute value for the last timestep
#         values = self.policy.predict_values(obs_as_tensor(new_obs, self.device))  # type: ignore[arg-type]
#
#     self.rollout_buffer.compute_returns_and_advantage(last_values=values, dones=dones)

#
# def bt_on_policy_train(self: OnPolicyAlgorithm, iteration: int, log_interval: int):
#     # Display training infos
#     if log_interval > 0 and iteration % log_interval == 0:
#         assert self.ep_info_buffer is not None
#         time_elapsed = max((time.time_ns() - self.start_time) / 1e9, sys.float_info.epsilon)
#         fps = int((self.num_timesteps - self._num_timesteps_at_start) / time_elapsed)
#         self.logger.record("time/iterations", iteration, exclude="tensorboard")
#         if len(self.ep_info_buffer) > 0 and len(self.ep_info_buffer[0]) > 0:
#             self.logger.record("rollout/ep_rew_mean", safe_mean([ep_info["r"] for ep_info in self.ep_info_buffer]))
#             self.logger.record("rollout/ep_len_mean", safe_mean([ep_info["l"] for ep_info in self.ep_info_buffer]))
#         self.logger.record("time/fps", fps)
#         self.logger.record("time/time_elapsed", int(time_elapsed), exclude="tensorboard")
#         self.logger.record("time/total_timesteps", self.num_timesteps, exclude="tensorboard")
#         self.logger.dump(step=self.num_timesteps)
#
#     self.train()
