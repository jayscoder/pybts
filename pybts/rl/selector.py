from py_trees import behaviour

from pybts.node import Node
from pybts.composites import Selector
from pybts.composites.composite import SEQ_SEL_tick
from pybts.rl.nodes import PPONode
import typing
import py_trees
import gymnasium as gym
from pybts import Status

# 获取并提交action
# yield status
# 获取状态，
class PPOSelector(Selector, PPONode):
    def __init__(self, name: str = '', children: typing.Optional[typing.List[py_trees.behaviour.Behaviour]] = None):
        Selector.__init__(self, name=name, children=children)
        PPONode.__init__(self, name=name)
        self._start_index = 0

    def bt_wrap_env(self, env: gym.Env) -> gym.Env:
        env.action_space = gym.spaces.Discrete(len(self.children))
        return env

    def step(self, action) -> typing.Iterator[Status]:
        self._start_index = action[0]
        yield Status.RUNNING

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        new_status = self.update()
        return SEQ_SEL_tick(
                self,
                tick_again_status=[Status.SUCCESS, Status.RUNNING],
                continue_status=[Status.FAILURE, Status.INVALID],
                no_child_status=Status.FAILURE,
                start_index=self._start_index)

