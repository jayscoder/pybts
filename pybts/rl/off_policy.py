import numpy as np
from gymnasium import spaces
from stable_baselines3.common.off_policy_algorithm import OffPolicyAlgorithm
from stable_baselines3.common.utils import (
    explained_variance, get_schedule_fn, safe_mean, obs_as_tensor,
    configure_logger, TrainFreq
)
from stable_baselines3 import SAC
import typing
from collections import deque
import sys
import gymnasium as gym
from abc import ABC, abstractmethod
from pybts.rl.common import DummyEnv
import sys
import time
import warnings
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

import numpy as np
from stable_baselines3.common.buffers import DictReplayBuffer, ReplayBuffer
from stable_baselines3.common.noise import ActionNoise, VectorizedActionNoise
from stable_baselines3.common.type_aliases import (
    GymEnv, MaybeCallback, RolloutReturn, Schedule, TrainFreq,
    TrainFrequencyUnit
)
from stable_baselines3.common.utils import safe_mean, should_collect_more_steps

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


def bt_off_policy_collect_rollouts(
        self: OffPolicyAlgorithm,
        train_freq: TrainFreq,
        replay_buffer: ReplayBuffer,
        action_noise: Optional[ActionNoise] = None,
        learning_starts: int = 0,
        log_interval: Optional[int] = None,
) -> typing.Generator:
    # Switch to eval mode (this affects batch norm / dropout)
    self.policy.set_training_mode(False)

    num_collected_steps, num_collected_episodes = 0, 0
    env_num_envs = 1
    assert train_freq.frequency > 0, "Should at least collect one step or episode."

    if self.use_sde:
        self.actor.reset_noise(env_num_envs)

    continue_training = True
    while should_collect_more_steps(train_freq, num_collected_steps, num_collected_episodes):
        if self.use_sde and self.sde_sample_freq > 0 and num_collected_steps % self.sde_sample_freq == 0:
            # Sample a new noise matrix
            self.actor.reset_noise(env_num_envs)

        # Select action randomly or according to policy
        actions, buffer_actions = self._sample_action(learning_starts, action_noise, env_num_envs)

        # Rescale and perform action
        new_obs, rewards, dones, infos = yield actions[0]
        # 数据都从单个处理成批量的
        new_obs = np.expand_dims(new_obs, axis=0)
        rewards = np.array([rewards])
        dones = np.array([dones])
        infos = [infos]

        self.num_timesteps += env_num_envs
        num_collected_steps += 1

        # Retrieve reward and episode length if using Monitor wrapper
        self._update_info_buffer(infos, dones)

        # Store data in replay buffer (normalized action and unnormalized observation)
        self._store_transition(replay_buffer, buffer_actions, new_obs, rewards, dones, infos)  # type: ignore[arg-type]

        self._update_current_progress_remaining(self.num_timesteps, self._total_timesteps)

        # For DQN, check if the target network should be updated
        # and update the exploration schedule
        # For SAC/TD3, the update is dones as the same time as the gradient update
        # see https://github.com/hill-a/stable-baselines/issues/900
        self._on_step()

        for idx, done in enumerate(dones):
            if done:
                # Update stats
                num_collected_episodes += 1
                self._episode_num += 1

                if action_noise is not None:
                    action_noise.reset()

                # Log training infos
                if log_interval is not None and self._episode_num % log_interval == 0:
                    self._dump_logs()

    return RolloutReturn(num_collected_steps * env_num_envs, num_collected_episodes, continue_training)

