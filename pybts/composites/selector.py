import py_trees
import typing
from py_trees.common import Status
from py_trees import behaviour
from pybts.composites.composite import Composite


class Selector(Composite):
    """
    组合节点：选择节点 ?
    依次顺序执行子节点
    - 当前执行节点返回 FAILURE/INVALID，继续执行后续节点
    - 当前执行节点返回 RUNNING，停止执行后续节点，下次执行还是从这个节点开始
    - 当前执行节点返回 SUCCESS，停止执行后续节点，下次执行从第一个节点开始
    返回最后一个执行节点的状态，如果没有孩子，则返回FAILURE
    """

    def gen_index(self):
        # 想要过滤掉前面的节点的话，可以继承Selector然后重写这个函数
        return 0

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        if self.reactive:
            return self.seq_sel_tick(
                    tick_again_status=[],
                    continue_status=[Status.FAILURE, Status.INVALID],
                    no_child_status=Status.FAILURE,
                    start_index=lambda _: self.gen_index())
        elif self.memory:
            return self.seq_sel_tick(
                    tick_again_status=[Status.SUCCESS, Status.RUNNING],
                    continue_status=[Status.FAILURE, Status.INVALID],
                    no_child_status=Status.FAILURE,
                    start_index=lambda _: self.gen_index())
        else:
            return self.seq_sel_tick(
                    tick_again_status=[Status.RUNNING],
                    continue_status=[Status.FAILURE, Status.INVALID],
                    no_child_status=Status.FAILURE,
                    start_index=lambda _: self.gen_index())


class SelectorWithMemory(Selector):
    """
    记忆选择节点
    - 当前执行节点返回 FAILURE/INVALID，继续执行后续节点
    - 当前执行节点返回 SUCCESS/RUNNING，停止执行后续节点，下次执行还是从这个节点开始
    返回最后一个执行节点的状态，如果没有孩子，则返回FAILURE
    """

    @property
    def memory(self) -> bool:
        return True

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        return self.seq_sel_tick(
                tick_again_status=[Status.SUCCESS, Status.RUNNING],
                continue_status=[Status.FAILURE, Status.INVALID],
                no_child_status=Status.FAILURE,
                start_index=lambda _: self.gen_index())


class ReactiveSelector(Selector):
    """
    反应式选择节点
    依次顺序执行子节点
    - 当前执行节点返回 FAILURE/INVALID，继续执行后续节点
    - 当前执行节点返回 SUCCESS/RUNNING，停止执行后续节点，下次执行从第一个节点开始
    返回最后一个执行节点的状态，如果没有孩子，则返回FAILURE
    """

    @property
    def reactive(self) -> bool:
        return True

    def tick(self) -> typing.Iterator[behaviour.Behaviour]:
        return self.seq_sel_tick(
                tick_again_status=[],
                continue_status=[Status.FAILURE, Status.INVALID],
                no_child_status=Status.FAILURE,
                start_index=lambda _: self.gen_index())
