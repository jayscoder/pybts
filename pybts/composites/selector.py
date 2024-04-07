import py_trees
import typing
from py_trees.common import Status
from py_trees import behaviour
from pybts.composites.composite import Composite, SEQ_SEL_tick


class Selector(Composite):
    """
    组合节点：选择节点
    依次顺序执行子节点
    - 当前执行节点返回 FAILURE/INVALID，继续执行后续节点
    - 当前执行节点返回 RUNNING，停止执行后续节点，下次执行还是从这个节点开始
    - 当前执行节点返回 SUCCESS，停止执行后续节点，下次执行从第一个节点开始
    返回最后一个执行节点的状态，如果没有孩子，则返回FAILURE
    """

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        return SEQ_SEL_tick(
                self,
                tick_again_status=[Status.RUNNING],
                continue_status=[Status.FAILURE, Status.INVALID],
                no_child_status=Status.FAILURE,
                start_index=0)


class SelectorWithMemory(Selector):
    """
    记忆选择节点
    - 当前执行节点返回 FAILURE/INVALID，继续执行后续节点
    - 当前执行节点返回 SUCCESS/RUNNING，停止执行后续节点，下次执行还是从这个节点开始
    - 当前执行节点返回 SUCCESS，停止执行后续节点，下次执行从第一个节点开始
    返回最后一个执行节点的状态，如果没有孩子，则返回FAILURE
    """

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        return SEQ_SEL_tick(
                self,
                tick_again_status=[Status.SUCCESS, Status.RUNNING],
                continue_status=[Status.FAILURE, Status.INVALID],
                no_child_status=Status.FAILURE,
                start_index=0)


class ReactiveSelector(Selector):
    """
    反应式选择节点
    依次顺序执行子节点
    - 当前执行节点返回 FAILURE/INVALID，继续执行后续节点
    - 当前执行节点返回 SUCCESS/RUNNING，停止执行后续节点，下次执行从第一个节点开始
    返回最后一个执行节点的状态，如果没有孩子，则返回FAILURE
    """

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        return SEQ_SEL_tick(
                self,
                tick_again_status=[],
                continue_status=[Status.FAILURE, Status.INVALID],
                no_child_status=Status.FAILURE,
                start_index=0)
