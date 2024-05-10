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

from abc import ABC, abstractmethod


class RLHandler(ABC):

    @abstractmethod
    def reset(self):
        raise NotImplementedError

    @abstractmethod
    def predict(self) -> (np.ndarray, np.ndarray, np.ndarray):
        """

        :return: action, values, log_probs
        """
        raise NotImplementedError

    @abstractmethod
    def observe(self, actions: np.ndarray, rewards: float, new_obs: typing.Any, dones: bool, infos: dict,
                values=None, log_probs=None) -> bool:
        raise NotImplementedError

    @abstractmethod
    def train(self):
        raise NotImplementedError
