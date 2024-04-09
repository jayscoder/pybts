import py_trees
import typing
from py_trees.common import Status
from pybts.composites.parallel import Parallel
from pybts.node import Condition


class PreCondition(Parallel, Condition):
    """前置条件"""

    @property
    def success_count(self) -> int:
        """
        成功数量
        """
        count = [1 for c in self.children if c.status == Status.SUCCESS]
        return sum(count)

    @property
    def success_ratio(self):
        """成功比例，0-1之间"""
        return self.success_count / len(self.children)


class PostCondition(Parallel, Condition):
    """后置条件"""

    @property
    def success_count(self) -> int:
        """
        成功数量
        """
        count = [1 for c in self.children if c.status == Status.SUCCESS]
        return sum(count)

    @property
    def success_ratio(self):
        """成功比例，0-1之间"""
        return self.success_count / len(self.children)
