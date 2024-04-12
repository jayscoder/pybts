import py_trees
import typing

from py_trees.behaviour import Behaviour
from py_trees.common import Status
from py_trees import behaviour
from pybts.composites.composite import Composite
import random


class Switcher(Composite):
    """
    选择其中一个子节点执行
    - 当前执行节点返回 RUNNING，下次执行还是从这个节点开始
    返回当前执行节点的状态

    index:
    - 具体的数字
    - jinja2模版: 从context中获取
    - random: 随机数
    """

    def __init__(self, index: typing.Union[int, str] = 'random', **kwargs):
        super().__init__(**kwargs)
        self.index = index
        self.curr_index = None

    def reset(self):
        super().reset()
        self.curr_index = None

    def to_data(self):
        return {
            **super().to_data(),
            'curr_index': self.curr_index
        }

    def tick(self) -> typing.Iterator[Behaviour]:
        if self.index == 'random':
            self.curr_index = random.randint(0, len(self.children) - 1)
        else:
            self.curr_index = self.converter.int(self.index)
        return self.switch_tick(index=self.curr_index, tick_again_status=[Status.RUNNING])


class ReactiveSwitcher(Switcher):
    """
    相应式选择其中一个子节点执行，每次都会重新选择index
    返回当前执行节点的状态
    """

    def tick(self) -> typing.Iterator[Behaviour]:
        return self.switch_tick(index=self.converter.int(self.index), tick_again_status=[])
