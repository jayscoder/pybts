from pybts.composites.composite import Composite
from pybts.composites.sequence import Sequence
from pybts.composites.selector import Selector
import py_trees
from pybts.node import Node
from abc import ABC
import typing
from py_trees.common import Status
from py_trees import behaviour
import itertools
import uuid


class Parallel(Composite):
    """
    组合节点：并行节点
    同时执行所有子节点，并根据成功阈值来决定返回状态
    - 如果有子节点返回 RUNNING 状态，节点本身返回 RUNNING
    - 子节点的执行不依赖于其它子节点的状态；每个子节点独立执行
    - 如果达到或超过指定的成功阈值（success_threshold），则返回 SUCCESS
    - 如果未达到成功阈值，即使所有子节点都已完成执行，也返回 FAILURE
    - RUNNING 状态的子节点在下一次tick时会继续执行，非RUNNING状态的子节点在下一次tick时会重置并重新开始
    - success_threshold 设置为 -1 表示所有子节点都必须成功才算总体成功
    """

    def __init__(
            self,
            success_threshold: int = 1,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.success_threshold = success_threshold

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(
                success_threshold=int(d.get('success_threshold', 1)),
                children=c,
                **d
        )

    def tick(self) -> typing.Iterator[py_trees.behaviour.Behaviour]:
        """
            同时执行所有子节点，并根据成功阈值来决定返回状态
            - 如果有子节点返回 RUNNING 状态，节点本身返回 RUNNING
            - 子节点的执行不依赖于其它子节点的状态；每个子节点独立执行
            - 如果达到或超过指定的成功阈值（success_threshold），则返回 SUCCESS
            - 如果未达到成功阈值，即使所有子节点都已完成执行，也返回 FAILURE
            - RUNNING 状态的子节点在下一次tick时会继续执行，非RUNNING状态的子节点在下一次tick时会重置并重新开始
            - success_threshold 设置为 -1 表示所有子节点都必须成功才算总体成功
            """
        self.debug_info['tick_count'] += 1
        self.logger.debug("%s.tick()" % (self.__class__.__name__))

        self.current_child = None

        for i, child in enumerate(self.children):
            self.current_child = child
            yield from child.tick()

        running_nodes = [child for child in self.children if child.status == Status.RUNNING]
        success_nodes = [child for child in self.children if child.status == Status.SUCCESS]

        success_threshold = self.success_threshold
        if success_threshold == -1:
            success_threshold = len(self.children)
        if len(running_nodes) > 0:
            new_status = Status.RUNNING
        elif len(success_nodes) >= success_threshold:
            # 超过这个数量的节点成功了，才算成功
            new_status = Status.SUCCESS
        else:
            # 否则就认为执行失败
            new_status = Status.FAILURE

        # if new_status != Status.RUNNING:
        #     self.stop(new_status)

        self.status = new_status
        yield self

    def to_data(self):
        return {
            **super().to_data(),
            'success_threshold': self.success_threshold
        }

# class ReactiveParallel(Parallel):
#     """
#     反应式并行节点
#     忽略RUNNING节点的并行节点
#     """
#
#     def tick(self) -> typing.Iterator[py_trees.behaviour.Behaviour]:
#         return _PAR_tick(self, tick_again_status=None, success_threshold=self.success_threshold)


# def _PAR_tick(self: Parallel, tick_again_status: typing.Optional[Status], success_threshold: int):
#     """
#     同时执行所有子节点，并根据成功阈值来决定返回状态
#     - 如果有子节点返回 RUNNING 状态，节点本身返回 RUNNING
#     - 子节点的执行不依赖于其它子节点的状态；每个子节点独立执行
#     - 如果达到或超过指定的成功阈值（success_threshold），则返回 SUCCESS
#     - 如果未达到成功阈值，即使所有子节点都已完成执行，也返回 FAILURE
#     - RUNNING 状态的子节点在下一次tick时会继续执行，非RUNNING状态的子节点在下一次tick时会重置并重新开始
#     - success_threshold 设置为 -1 表示所有子节点都必须成功才算总体成功
#     """
#     self._tick_count += 1
#     self.logger.debug("%s.tick()" % (self.__class__.__name__))
#
#     if self.status == tick_again_status:
#         # 重新执行上次执行的子节点
#         assert len(self.tick_again_index) > 0
#     else:
#         self.current_child = None
#         self.tick_again_index = set()
#
#     for i, child in enumerate(self.children):
#         if len(self.tick_again_index) > 0 and i not in self.tick_again_index:
#             continue
#         self.current_child = child
#         for node in child.tick():
#             yield node
#         if child.status == tick_again_status:
#             self.tick_again_index.add(i)
#
#     if len(self.tick_again_index) > 0:
#         new_status = tick_again_status
#     else:
#         successful = [child for child in self.children if child.status == Status.SUCCESS]
#         if success_threshold == -1:
#             success_threshold = len(self.children)
#         if len(successful) >= success_threshold:
#             # 超过这个数量的节点成功了，才算成功
#             new_status = Status.SUCCESS
#         else:
#             new_status = Status.FAILURE
#
#     # if new_status != Status.RUNNING:
#     #     self.stop(new_status)
#
#     self.status = new_status
#     yield self
