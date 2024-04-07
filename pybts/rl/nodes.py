import typing
from typing import Any, SupportsFloat

from gymnasium.core import ActType, ObsType
from py_trees.common import Status

from pybts.node import Node
from pybts.node import Action
from pybts.composites import Composite, Selector, Sequence
from stable_baselines3 import PPO
from stable_baselines3.common.base_class import BaseAlgorithm
import stable_baselines3
from stable_baselines3.common.utils import obs_as_tensor, safe_mean
import py_trees
import gymnasium as gym
from abc import ABC, abstractmethod
import numpy as np
import torch as th
from gymnasium import spaces


class PPONode(Action, PPO, ABC):
    def __init__(self, name: str = '', n_steps: int = 100, train_mode: bool = False):
        super().__init__(name=name)
        self.n_steps = n_steps
        self.train_mode = train_mode
        self.step_result = {
            'obs'   : None,
            'reward': None,
            'done'  : None,
            'info'  : { }
        }

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(
                name=d['name'],
                n_steps=d.get('n_steps', 100),
                train_mode=d.get('train_mode', False)
        )

    def setup(self, **kwargs: typing.Any) -> None:
        env = kwargs['env']
        PPO.__init__(self, 'MlpPolicy', verbose=1, device='cpu', env=self.bt_wrap_env(env), n_steps=self.n_steps)

    def bt_wrap_env(self, env: gym.Env) -> gym.Env:
        return env

    def step(self, action) -> typing.Iterator[Status]:
        self.actions.put_nowait(action)
        yield Status.RUNNING
        obs, reward, done, info = self.env.step(action)
        self.step_result = {
            'obs'   : obs,
            'reward': reward,
            'done'  : done,
            'info'  : None
        }

    def train_updater(self) -> typing.Iterator[Status]:
        assert self._last_obs is not None, "No previous observation was provided"
        # Switch to eval mode (this affects batch norm / dropout)
        self.policy.set_training_mode(False)
        n_steps = 0
        self.rollout_buffer.reset()
        # Sample new weights for the state dependent exploration
        if self.use_sde:
            self.policy.reset_noise(1)

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

            for status in self.step(clipped_actions):
                yield status
            new_obs = self.step_result['obs']
            reward = self.step_result['reward']
            rewards = np.array([reward])
            done = self.step_result['done']
            dones = np.array([done])
            info = self.step_result['info']
            infos = [info]

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

        # self.callback.update_locals(locals())
        self.train()
        # callback.on_rollout_end()
        yield Status.SUCCESS

    def eval_updater(self) -> typing.Iterator:
        # Switch to eval mode (this affects batch norm / dropout)
        self.policy.set_training_mode(False)
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

        # self.actions.put_nowait(clipped_actions)
        for status in self.step(clipped_actions):
            yield status

        new_obs = self.step_result['obs']
        reward = self.step_result['reward']
        rewards = np.array([reward])
        done = self.step_result['done']
        dones = np.array([done])
        info = self.step_result['info']
        infos = [info]

        self._last_obs = new_obs  # type: ignore[assignment]
        self._last_episode_starts = dones

    def updater(self) -> typing.Iterator[Status]:
        if self.train_mode:
            yield from self.train_updater()
        else:
            yield from self.eval_updater()

