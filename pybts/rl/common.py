from __future__ import annotations
from typing import Any, SupportsFloat

import gymnasium as gym
from gymnasium.core import ActType, ObsType, WrapperObsType
from pybts.nodes import Status, Node


class DummyEnv(gym.Env):
    def __init__(self,
                 obs: ObsType,
                 info: dict,
                 action_space: gym.spaces.Space,
                 observation_space: gym.spaces.Space,
                 ):
        self.obs = obs
        self.info = info
        self.action_space = action_space
        self.observation_space = observation_space

    def step(
            self, action: ActType
    ) -> tuple[ObsType, SupportsFloat, bool, bool, dict[str, Any]]:
        raise Exception('不能step')

    def reset(
            self,
            *,
            seed: int | None = None,
            options: dict[str, Any] | None = None,
    ) -> tuple[ObsType, dict[str, Any]]:
        print('DummyEnv reset')
        return self.obs, self.info


OFF_POLICY_ALGOS = ['SAC', 'TD3', 'DDPG', 'DQN']  # 离线策略算法
ON_POLICY_ALGOS = ['PPO', 'TRPO', 'A2C']  # 在线策略算法


def is_off_policy_algo(algo: str) -> bool:
    """是否是离线策略算法 Off-Policy"""
    algo = algo.upper()
    for a in OFF_POLICY_ALGOS:
        if a in algo:
            return True
    return False


def is_on_policy_algo(algo: str) -> bool:
    """是否是在线策略算法 On-Policy"""
    algo = algo.upper()
    for a in ON_POLICY_ALGOS:
        if a in algo:
            return True
    return False


STATUS_ID = {
    Status.INVALID: 0,
    Status.SUCCESS: 1,
    Status.FAILURE: 2,
    Status.RUNNING: 3
}


def children_status_ids(node: Node) -> list[int]:
    return [STATUS_ID[c.status] for c in node.children]
