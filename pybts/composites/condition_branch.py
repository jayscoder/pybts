from py_trees.behaviour import Behaviour
import typing
from py_trees.common import Status
from pybts.composites.composite import Composite


class CondBranch(Composite):
    """
    条件分支节点
    只能有2或3个子节点

    也可以起到打断RUNNING节点的效果（由前面的条件节点来判断是否要进行打断）

    2个子节点，当前面的节点执行成功时，执行第二个节点
    等同于
    <ReactiveSequence>
        <Children[0]>
        <Children[1]>
    </ReactiveSequence>

    3个子节点，当前面的节点执行成功时，执行第二个节点，否则执行第三个节点
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

    def setup(self, **kwargs: typing.Any) -> None:
        super().setup(**kwargs)
        assert len(self.children) in [2, 3], 'ConditionBranch must have 2 or 3 children'

    def cond_tick(self: Composite, tick_again_status: list[Status]):
        if self.status in tick_again_status and self.current_index != 0:
            assert self.current_child is not None
            # 重新执行上次执行的动作节点
            yield from self.current_child.tick()
            new_status = self.current_child.status
            if new_status != Status.RUNNING:
                self.stop(new_status)
            self.status = new_status
            yield self
            return

        condition = self.children[0]
        self.current_child = condition
        yield from condition.tick()

        if condition.status == Status.RUNNING:
            self.status = Status.RUNNING
            yield self
            return

        if condition.status == Status.SUCCESS:
            # 执行第1个节点
            self.current_child = self.children[1]
        elif condition.status == Status.FAILURE:
            # 执行第2个节点（如果第二个节点存在的话）
            if len(self.children) == 3:
                self.current_child = self.children[2]
            else:
                self.current_child = None

        for child in self.children[1:]:
            # 停止其他节点
            if child != self.current_child:
                child.stop(Status.INVALID)

        # 执行选择的子节点
        if self.current_child is not None:
            yield from self.current_child.tick()
            new_status = self.current_child.status
        else:
            new_status = condition.status
        if new_status != Status.RUNNING:
            self.stop(new_status)
        self.status = new_status
        yield self

    def tick(self) -> typing.Iterator[Behaviour]:
        if self.reactive:
            return self.cond_tick(tick_again_status=[])
        elif self.memory:
            return self.cond_tick(tick_again_status=[Status.RUNNING, Status.FAILURE])
        else:
            return self.cond_tick(tick_again_status=[Status.RUNNING])


class ConditionBranch(CondBranch):
    """条件分支节点的别名"""
    pass


class ReactiveCondBranch(CondBranch):

    def reactive(self) -> bool:
        return True


class CondBranchWithMemory(CondBranch):

    def memory(self) -> bool:
        return True
