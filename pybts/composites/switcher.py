from __future__ import annotations
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

    def gen_index(self) -> int:
        if self.index == 'random':
            return random.randint(0, len(self.children) - 1)
        else:
            return self.converter.int(self.index)

    def tick_again_status(self: Composite):
        """计算需要重新执行的状态"""
        if self.reactive:
            return []
        elif self.memory:
            return [Status.RUNNING, Status.FAILURE]
        else:
            return [Status.RUNNING]

    def tick(self) -> typing.Iterator[Behaviour]:
        return self.switch_tick(index=lambda _: self.gen_index(), tick_again_status=self.tick_again_status())


class ReactiveSwitcher(Switcher):
    """
    相应式选择其中一个子节点执行，每次都会重新选择index
    返回当前执行节点的状态
    """

    @property
    def reactive(self) -> bool:
        return True

    def tick(self) -> typing.Iterator[Behaviour]:
        return self.switch_tick(index=lambda _: self.gen_index(), tick_again_status=[])
