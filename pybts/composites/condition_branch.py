import py_trees
from py_trees.behaviour import Behaviour

from pybts.node import Node
from abc import ABC
import typing
from py_trees.common import Status
from py_trees import behaviour
import itertools
from pybts.composites.composite import Composite, SEQ_SEL_tick


class ConditionBranch(Composite):
    """
    条件分支节点
    只能有2或3个子节点

    也可以起到打断RUNNING节点的效果（由前面的条件节点来判断是否要进行打断）

    2个子节点
    等同于
    <ReactiveSequence>
        <Children[0]>
        <Children[1]>
    </ReactiveSequence>

    3个子节点
    等同于
    <Parallel>
        <ReactiveSequence>
            <Children[0]/>
            <Children[1]/>
        </ReactiveSequence>
        <ReactiveSelector>
            <Children[0]/>
            <Children[2]/>
        </ReactiveSelector>
    <Parallel>
    """

    def tick(self) -> typing.Iterator[Behaviour]:
        assert len(self.children) in [2, 3]
        condition = self.children[0]
        yield from condition.tick()

        exec_child = None  # 准备执行的节点
        if condition.status == Status.SUCCESS:
            # 执行第1个节点
            exec_child = self.children[1]
        elif condition.status == Status.FAILURE:
            # 执行第2个节点（如果第二个节点不存在，则返回失败）
            if len(self.children) == 3:
                exec_child = self.children[2]
        else:
            raise Exception('条件节点不能返回SUCCESS/FAILURE以外的状态')

        if self.status == Status.RUNNING:
            assert self.current_child is not None
            # 重新执行上次执行的子节点
            if self.current_child != exec_child:
                # 条件不匹配
                # 停止执行上次执行的节点
                self.current_child.stop(Status.INVALID)

        if exec_child is not None:
            self.current_child = exec_child
            yield from exec_child.tick()
        else:
            self.current_child = condition

        new_status = self.current_child.status

        # if new_status != Status.RUNNING:
        #     self.stop(new_status)

        self.status = new_status
        yield self
