import numpy as np
from gymnasium import spaces
from stable_baselines3.common.on_policy_algorithm import OnPolicyAlgorithm
from stable_baselines3.common.off_policy_algorithm import OffPolicyAlgorithm
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
from stable_baselines3.common.policies import ActorCriticPolicy
from typing import Union
from pybts.rl.off_policy import *
from pybts.rl.on_policy import *


class RLPolicyNode(ABC):
    """强化学习在线策略节点，拿来跟其他的Node多继承用"""

    def __init__(self):
        self.rl_collector = None
        self.rl_accum_reward = 0  # 当前累积奖励
        self.rl_info = None
        self.rl_reward = 0  # 当前奖励
        self.rl_obs = None
        self.rl_iteration = 0
        self.rl_done = False
        self.rl_action = None
        self.rl_model = None

    def reset(self):
        self.rl_accum_reward = 0

    def to_data(self):
        return {
            'rl_iteration'   : self.rl_iteration,
            'rl_policy'      : str(self.rl_policy()),
            'rl_info'        : self.rl_info,
            'rl_reward'      : self.rl_reward,
            'rl_obs'         : self.rl_obs,
            'rl_accum_reward': self.rl_accum_reward,
            'rl_action'      : self.rl_action,
            'rl_reward_scope': self.rl_reward_scope(),
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

    def rl_reward_scope(self) -> str:
        """
        奖励域

        例如：default
        多个奖励域用,分隔
        如果设置了奖励域，则生成本轮奖励时会从self.context.rl_reward[scope]里获取
        """
        return ''

    @abstractmethod
    def rl_gen_reward(self) -> float:
        reward_scope = self.rl_reward_scope()
        if reward_scope != '':
            assert isinstance(self, Node), 'RLOnPolicyNode 必须得继承Node节点'
            assert self.context is not None, 'context必须得设置好'
            assert 'rl_reward' in self.context, 'context必须得含有rl_reward键'
            scopes = reward_scope.split(',')
            curr_reward = 0
            for scope in scopes:
                curr_reward += self.context['rl_reward'].get(scope, 0)
            return curr_reward - self.rl_accum_reward
        raise NotImplemented

    @abstractmethod
    def rl_gen_done(self) -> bool:
        # 返回当前环境是否结束
        raise NotImplemented

    def rl_device(self) -> str:
        return 'cpu'

    def rl_policy(self) -> Union[str, typing.Type[ActorCriticPolicy]]:
        return 'MlpPolicy'

    @abstractmethod
    def rl_take_action(
            self,
            train: bool,
            log_interval: int = 1,
            save_interval: int = 5,
            save_path: str = ''
    ):
        if isinstance(self.rl_model, OnPolicyAlgorithm):
            return self._rl_on_policy_take_action(
                    train=train,
                    log_interval=log_interval,
                    save_interval=save_interval,
                    save_path=save_path)
        else:
            return self._rl_off_policy_take_action(
                    train=train,
                    log_interval=log_interval,
                    save_interval=save_interval,
                    save_path=save_path
            )

    def _rl_off_policy_take_action(
            self,
            train: bool,
            log_interval: int = 1,
            save_interval: int = 5,
            save_path: str = ''
    ):
        assert self.rl_model is not None, 'RL model not initialized'
        assert isinstance(self.rl_model, OffPolicyAlgorithm), 'RL model must be initialized with OffPolicyAlgorithm'
        model: OffPolicyAlgorithm = self.rl_model
        info = self.rl_gen_info()
        reward = self.rl_gen_reward()
        obs = self.rl_gen_obs()
        done = self.rl_gen_done()

        if train:
            try:
                if self.rl_collector is None:
                    self.rl_collector = bt_off_policy_collect_rollouts(
                            model,
                            train_freq=model.train_freq,
                            action_noise=model.action_noise,
                            learning_starts=model.learning_starts,
                            replay_buffer=model.replay_buffer,
                            log_interval=log_interval,
                    )
                    action = self.rl_collector.send(None)
                else:
                    info = info
                    action = self.rl_collector.send((obs, reward, done, info))

                if isinstance(action, RolloutReturn):
                    # 结束了
                    rollout: RolloutReturn = action
                    if model.num_timesteps > 0 and model.num_timesteps > model.learning_starts:
                        # If no `gradient_steps` is specified,
                        # do as many gradients steps as steps performed during the rollout
                        gradient_steps = model.gradient_steps if model.gradient_steps >= 0 else rollout.episode_timesteps
                        # Special case when the user passes `gradient_steps=0`
                        if gradient_steps > 0:
                            model.train(batch_size=model.batch_size, gradient_steps=gradient_steps)

                    self.rl_collector = bt_off_policy_collect_rollouts(
                            model,
                            train_freq=model.train_freq,
                            action_noise=model.action_noise,
                            learning_starts=model.learning_starts,
                            replay_buffer=model.replay_buffer,
                            log_interval=log_interval,
                    )
                    action = self.rl_collector.send(None)
            except StopIteration:
                self.rl_collector = None
                self.rl_iteration += 1
                # Display training infos

                if self.rl_iteration % save_interval == 0:
                    model.save(save_path)

                self.rl_collector = bt_off_policy_collect_rollouts(
                        model,
                        train_freq=model.train_freq,
                        action_noise=model.action_noise,
                        learning_starts=model.learning_starts,
                        replay_buffer=model.replay_buffer,
                        log_interval=log_interval,
                )
                action = self.rl_collector.send(None)
        else:
            # 预测模式
            action, state = model.predict(obs)

        self.rl_obs = obs
        self.rl_reward = reward
        self.rl_info = info
        self.rl_accum_reward += reward
        self.rl_action = action
        self.rl_done = done
        return action

    def _rl_on_policy_take_action(
            self,
            train: bool,
            log_interval: int = 1,
            save_interval: int = 5,
            save_path: str = ''
    ):
        assert self.rl_model is not None, 'RL model not initialized'
        assert isinstance(self.rl_model, OnPolicyAlgorithm), 'RL model must be an instance of OnPolicyAlgorithm'
        model: OnPolicyAlgorithm = self.rl_model
        info = self.rl_gen_info()
        reward = self.rl_gen_reward()
        obs = self.rl_gen_obs()
        done = self.rl_gen_done()
        if train:
            try:
                if self.rl_collector is None:
                    self.rl_collector = bt_on_policy_collect_rollouts(
                            model,
                            last_obs=obs)
                    action = self.rl_collector.send(None)
                else:
                    info = info
                    action = self.rl_collector.send((obs, reward, done, info))
            except StopIteration:
                self.rl_collector = None
                self.rl_iteration += 1
                # Display training infos
                bt_on_policy_train(model, iteration=self.rl_iteration, log_interval=log_interval)
                if self.rl_iteration % save_interval == 0:
                    model.save(save_path)

                self.rl_collector = bt_on_policy_collect_rollouts(
                        model,
                        last_obs=obs)
                action = self.rl_collector.send(None)
        else:
            # 预测模式
            action, state = model.predict(obs)

        self.rl_obs = obs
        self.rl_reward = reward
        self.rl_info = info
        self.rl_accum_reward += reward
        self.rl_action = action
        self.rl_done = done
        return action
