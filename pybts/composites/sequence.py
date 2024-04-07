import py_trees
from pybts.node import Node
from abc import ABC
import typing
from py_trees.common import Status
from py_trees import behaviour
import itertools
from pybts.composites.composite import Composite, SEQ_SEL_tick


class Sequence(Composite):
    """
    组合节点：顺序节点
    依次顺序执行子节点
    - 当前执行节点返回 SUCCESS，继续执行后续节点
    - 当前执行节点返回 RUNNING，停止执行后续节点，下次执行还是从这个节点开始
    - 当前执行节点返回 FAILURE/INVALID，停止执行后续节点，下次执行从第一个节点开始
    返回最后一个执行节点的状态，如果没有孩子，则返回SUCCESS
    """

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        return SEQ_SEL_tick(
                self,
                tick_again_status=[Status.RUNNING],
                continue_status=[Status.SUCCESS],
                no_child_status=Status.SUCCESS,
                start_index=0)


class SequenceWithMemory(Sequence):
    """
    记忆顺序节点
    依次顺序执行子节点
    - 当前执行节点返回 SUCCESS，继续执行后续节点
    - 当前执行节点返回 FAILURE/RUNNING，停止执行后续节点，下次执行还是从这个节点开始
    - 当前执行节点返回 INVALID，停止执行后续节点，下次执行从第一个节点开始
    返回最后一个执行节点的状态，如果没有孩子，则返回SUCCESS
    """

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        return SEQ_SEL_tick(
                self,
                tick_again_status=[Status.RUNNING, Status.FAILURE],
                continue_status=[Status.SUCCESS],
                no_child_status=Status.SUCCESS,
                start_index=0)


class ReactiveSequence(Sequence):
    """
    反应式顺序节点
    依次顺序执行子节点
    - 当前执行节点返回 SUCCESS，继续执行后续节点
    - 当前执行节点返回 FAILURE/RUNNING/INVALID，停止执行后续节点，下次执行从第一个节点开始
    返回最后一个执行节点的状态，如果没有孩子，则返回SUCCESS

    可以起到打断后续RUNNING节点的效果
    - 如果前面的节点返回SUCCESS，则后续的RUNNING节点会继续运行，否则就会打断掉
    """

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        return SEQ_SEL_tick(
                self,
                tick_again_status=[],
                continue_status=[Status.SUCCESS],
                no_child_status=Status.SUCCESS,
                start_index=0)
