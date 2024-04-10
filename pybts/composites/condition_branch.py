from py_trees.behaviour import Behaviour
import typing
from py_trees.common import Status
from pybts.composites.composite import Composite


class ConditionBranch(Composite):
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

    def tick(self) -> typing.Iterator[Behaviour]:
        condition = self.children[0]
        self.current_child = condition

        yield from condition.tick()

        exec_child = None  # 准备执行的节点

        if condition.status == Status.SUCCESS:
            # 执行第1个节点
            exec_child = self.children[1]
        elif condition.status == Status.FAILURE:
            # 执行第2个节点（如果第二个节点存在的话）
            if len(self.children) == 3:
                exec_child = self.children[2]

        if condition.status != Status.RUNNING:
            # 如果条件的状态是RUNNING，则不停止其他节点
            for child in self.children[1:]:
                # 停止其他节点
                if child != exec_child:
                    child.stop(Status.INVALID)

        # 执行选择的子节点
        if exec_child is not None:
            self.current_child = exec_child
            yield from exec_child.tick()

        new_status = self.current_child.status
        self.status = new_status
        yield self
