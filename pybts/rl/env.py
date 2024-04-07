from typing import Any, SupportsFloat

import gymnasium as gym
from abc import ABC, abstractmethod

from gymnasium.core import WrapperActType, WrapperObsType
from queue import Queue



class BTEnv(gym.Wrapper):
    env: gym.Env

    def __init__(self, env: gym.Env):
        super().__init__(env=env)
        self.actions = Queue()

    @property
    def time(self) -> float:
        return 0

    def post_action(self, action: any):
        self.actions.put_nowait(action)

    def gen_obs(self, **kwargs):
        """获取当前的观测"""
        return self.env.observation_space.sample()

    def gen_reward(self, **kwargs):
        """获取当前的奖励"""
        return 0

    def step(
            self, action: WrapperActType
    ) -> tuple[WrapperObsType, SupportsFloat, bool, bool, dict[str, Any]]:
        self.post_action(action)
        return self.env.step(action)

    def update(self):
        # 更新环境
        pass
