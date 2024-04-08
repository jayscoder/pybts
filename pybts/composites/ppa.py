import py_trees
import typing
from py_trees.common import Status
from py_trees import behaviour
from pybts.composites.composite import Composite, SEQ_SEL_tick
from pybts.composites.sequence import Sequence, SEQ_SEL_tick
from pybts.node import Condition

class PreCondition(Sequence, Condition):
    """前置条件"""
    def score(self):
        """满足评分"""
        count = [1 for c in self.children if c.status == Status.SUCCESS]
        return sum(count) / len(count)

class PostCondition(Sequence, Condition):
    """后置条件"""
    def score(self):
        """满足评分"""
        count = [1 for c in self.children if c.status == Status.SUCCESS]
        return sum(count) / len(count)
