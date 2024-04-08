import gymnasium as gym
from gymnasium import spaces
from gymnasium.core import ObsType, WrapperObsType


class DummyEnv(gym.Wrapper):
    def __init__(self,
                 env: gym.Env,
                 action_space: gym.spaces.Space,
                 observation_space: gym.spaces.Space,
                 ):
        super().__init__(env)
        self.env = env
        self._action_space = action_space
        self._observation_space = observation_space
