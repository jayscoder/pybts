import numpy as np
from gymnasium import spaces
from stable_baselines3.common.on_policy_algorithm import OnPolicyAlgorithm
from stable_baselines3.common.utils import (
    explained_variance, get_schedule_fn, safe_mean, obs_as_tensor,
    configure_logger
)
from stable_baselines3 import PPO
import typing
import torch as th
from pybts.node import Node
import time
from collections import deque
import sys
import gymnasium as gym
from abc import ABC, abstractmethod
from pybts.rl.common import DummyEnv


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


def bt_on_policy_collect_rollouts(self: OnPolicyAlgorithm, last_obs) -> typing.Generator:
    """
    Collect rollouts from an OnPolicyAlgorithm
    :param self:
    :param last_obs: last observation

    collector = bt_on_policy_collect_rollouts(model, last_obs)
    action = next(collector)
    obs, reward, terminated, truncated, info = env.step(action)
    collector.send(obs, reward, terminated or truncated, info)
    """
    # Switch to eval mode (this affects batch norm / dropout)
    self.policy.set_training_mode(False)
    n_steps = 0
    self.rollout_buffer.reset()
    # Sample new weights for the state dependent exploration
    if self.use_sde:
        self.policy.reset_noise(1)

    self._last_obs = np.expand_dims(last_obs, axis=0)

    # callback.on_rollout_start()
    while n_steps < self.n_steps:
        if self.use_sde and self.sde_sample_freq > 0 and n_steps % self.sde_sample_freq == 0:
            # Sample a new noise matrix
            self.policy.reset_noise(1)

        with th.no_grad():
            # Convert to pytorch tensor or to TensorDict
            obs_tensor = obs_as_tensor(self._last_obs, self.device)
            actions, values, log_probs = self.policy(obs_tensor)
        actions = actions.cpu().numpy()

        # Rescale and perform action
        clipped_actions = actions

        if isinstance(self.action_space, spaces.Box):
            if self.policy.squash_output:
                # Unscale the actions to match env bounds
                # if they were previously squashed (scaled in [-1, 1])
                clipped_actions = self.policy.unscale_action(clipped_actions)
            else:
                # Otherwise, clip the actions to avoid out of bound error
                # as we are sampling from an unbounded Gaussian distribution
                clipped_actions = np.clip(actions, self.action_space.low, self.action_space.high)

        new_obs, rewards, dones, infos = yield clipped_actions[0]
        # 数据都从单个处理成批量的
        new_obs = np.expand_dims(new_obs, axis=0)
        rewards = np.array([rewards])
        dones = np.array([dones])
        infos = [infos]

        self.num_timesteps += 1

        # Give access to local variables
        # callback.update_locals(locals())
        # if not callback.on_step():
        #     return False

        self._update_info_buffer(infos, dones)
        n_steps += 1

        if isinstance(self.action_space, spaces.Discrete):
            # Reshape in case of discrete action
            actions = actions.reshape(-1, 1)

        # Handle timeout by bootstraping with value function
        # see GitHub issue #633
        for idx, done in enumerate(dones):
            if (
                    done
                    and infos[idx].get("terminal_observation") is not None
                    and infos[idx].get("TimeLimit.truncated", False)
            ):
                terminal_obs = self.policy.obs_to_tensor(infos[idx]["terminal_observation"])[0]
                with th.no_grad():
                    terminal_value = self.policy.predict_values(terminal_obs)[0]  # type: ignore[arg-type]
                rewards[idx] += self.gamma * terminal_value

        self.rollout_buffer.add(
                self._last_obs,  # type: ignore[arg-type]
                actions,
                rewards,
                self._last_episode_starts,  # type: ignore[arg-type]
                values,
                log_probs,
        )
        self._last_obs = new_obs  # type: ignore[assignment]
        self._last_episode_starts = dones

    with th.no_grad():
        # Compute value for the last timestep
        values = self.policy.predict_values(obs_as_tensor(new_obs, self.device))  # type: ignore[arg-type]

    self.rollout_buffer.compute_returns_and_advantage(last_values=values, dones=dones)


def bt_on_policy_train(self: OnPolicyAlgorithm, iteration: int, log_interval: int):
    # Display training infos
    if log_interval > 0 and iteration % log_interval == 0:
        assert self.ep_info_buffer is not None
        time_elapsed = max((time.time_ns() - self.start_time) / 1e9, sys.float_info.epsilon)
        fps = int((self.num_timesteps - self._num_timesteps_at_start) / time_elapsed)
        self.logger.record("time/iterations", iteration, exclude="tensorboard")
        if len(self.ep_info_buffer) > 0 and len(self.ep_info_buffer[0]) > 0:
            self.logger.record("rollout/ep_rew_mean", safe_mean([ep_info["r"] for ep_info in self.ep_info_buffer]))
            self.logger.record("rollout/ep_len_mean", safe_mean([ep_info["l"] for ep_info in self.ep_info_buffer]))
        self.logger.record("time/fps", fps)
        self.logger.record("time/time_elapsed", int(time_elapsed), exclude="tensorboard")
        self.logger.record("time/total_timesteps", self.num_timesteps, exclude="tensorboard")
        self.logger.dump(step=self.num_timesteps)

    self.train()


class RLOnPolicyNode(ABC):
    """强化学习在线策略节点，拿来多继承用"""

    def __init__(self):
        self.rl_on_policy_collector = None
        self.rl_accum_reward = 0
        self.rl_info = None
        self.rl_reward = 0 # 当前奖励
        self.rl_obs = None
        self.rl_iteration = 0
        self.rl_action = None
        self.rl_model: typing.Optional[OnPolicyAlgorithm] = None

    def reset(self):
        self.rl_accum_reward = 0

    def to_data(self):
        return {
            'rl_iteration'   : self.rl_iteration,
            'rl_info'        : self.rl_info,
            'rl_reward'      : self.rl_reward,
            'rl_obs'         : self.rl_obs,
            'rl_accum_reward': self.rl_accum_reward,
            'rl_action'      : self.rl_action
        }

    @abstractmethod
    def rl_env(self) -> gym.Env:
        raise NotImplemented

    @abstractmethod
    def rl_action_space(self) -> gym.spaces.Space:
        raise NotImplemented

    @abstractmethod
    def rl_observation_space(self) -> gym.spaces.Space:
        raise NotImplemented

    @abstractmethod
    def rl_gen_obs(self):
        raise NotImplemented

    @abstractmethod
    def rl_gen_info(self) -> dict:
        raise NotImplemented

    @abstractmethod
    def rl_gen_reward(self) -> float:
        raise NotImplemented

    def rl_take_action(self,
                       train: bool,
                       log_interval: int = 1,
                       save_interval: int = 5,
                       save_path: str = ''
                       ):
        assert self.rl_model is not None, 'RL model not initialized'
        model = self.rl_model
        info = self.rl_gen_info()
        reward = self.rl_gen_reward()
        obs = self.rl_gen_obs()

        if train:
            try:
                if self.rl_on_policy_collector is None:
                    self.rl_on_policy_collector = bt_on_policy_collect_rollouts(
                            model,
                            last_obs=obs)
                    action = self.rl_on_policy_collector.send(None)
                else:
                    info = info
                    action = self.rl_on_policy_collector.send(
                            (obs, reward, info['terminated'] or info['truncated'], info))
            except StopIteration:
                self.rl_on_policy_collector = None
                self.rl_iteration += 1
                # Display training infos
                bt_on_policy_train(model, iteration=self.rl_iteration, log_interval=log_interval)
                if self.rl_iteration % save_interval == 0:
                    model.save(save_path)

                self.rl_on_policy_collector = bt_on_policy_collect_rollouts(
                        model,
                        last_obs=obs)
                action = self.rl_on_policy_collector.send(None)
        else:
            # 预测模式
            action, state = model.predict(obs)

        self.rl_obs = obs
        self.rl_reward = reward
        self.rl_info = info
        self.rl_accum_reward += reward
        self.rl_action = action
        return action

    def rl_ppo_setup_model(self,
                           train: bool,
                           path: str,
                           policy: str,
                           tensorboard_log: str = '',
                           verbose: int = 1,
                           n_steps: int = 8,
                           batch_size: int = 8,
                           tb_log_name: str = ''
                           ):
        env = DummyEnv(
                env=self.rl_env(),
                action_space=self.rl_action_space(),
                observation_space=self.rl_observation_space())
        model: typing.Optional[OnPolicyAlgorithm] = None

        if path != '':
            try:
                model = PPO.load(
                        path=path,
                        env=env,
                        tensorboard_log=tensorboard_log,
                        verbose=verbose,
                        force_reset=False,
                        n_steps=n_steps,
                        batch_size=batch_size,
                )
            except:
                pass
        if model is None:
            model = PPO(
                    policy=policy,
                    env=env,
                    verbose=1,
                    tensorboard_log=tensorboard_log,
                    n_steps=8,
                    batch_size=8,
            )

        if train:
            bt_on_policy_setup_learn(
                    model,
                    obs=self.rl_gen_obs(),
                    tb_log_name=tb_log_name
            )

        self.rl_model = model
        return model

# def bt_on_policy_predict(model: OnPolicyAlgorithm, last_obs):
#     model.predict()
#     # Switch to eval mode (this affects batch norm / dropout)
#     model._last_obs = last_obs
#     model.policy.set_training_mode(False)
#     with th.no_grad():
#         # Convert to pytorch tensor or to TensorDict
#         obs_tensor = obs_as_tensor(model._last_obs, model.device)
#         actions, values, log_probs = model.policy(obs_tensor)
#     actions = actions.cpu().numpy()
#     # Rescale and perform action
#     clipped_actions = actions
#
#     if isinstance(model.action_space, spaces.Box):
#         if model.policy.squash_output:
#             # Unscale the actions to match env bounds
#             # if they were previously squashed (scaled in [-1, 1])
#             clipped_actions = model.policy.unscale_action(clipped_actions)
#         else:
#             # Otherwise, clip the actions to avoid out of bound error
#             # as we are sampling from an unbounded Gaussian distribution
#             clipped_actions = np.clip(actions, model.action_space.low, model.action_space.high)
#
#     # self.actions.put_nowait(clipped_actions)
#     return clipped_actions
