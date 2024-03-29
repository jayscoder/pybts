from __future__ import annotations
from abc import ABC
from queue import Queue
from pybts.constants import *
import typing
import py_trees


class Node(py_trees.behaviour.Behaviour, ABC):
    """
    Base class for all nodes in the behavior tree
    """

    def __init__(self, name: str = ''):
        super().__init__(name=name or self.__class__.__name__)

    def reset(self):
        pass

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(name=d['name'])

    def to_data(self):
        # 在board上查看的信息
        return { }

    def update(self) -> Status:
        return Status.INVALID


class Composite(py_trees.composites.Composite, Node, ABC):
    def __init__(
            self,
            name: str = 'Composite',
            children: typing.Optional[typing.List[py_trees.behaviour.Behaviour]] = None,
    ):
        super().__init__(name=name, children=children)


class Decorator(py_trees.decorators.Decorator, Node, ABC):
    def __init__(self, child: py_trees.behaviour.Behaviour, name: str = 'Decorator'):
        super().__init__(name=name, child=child)


class Sequence(py_trees.composites.Sequence, Composite):
    def __init__(
            self,
            name: str = 'Sequence',
            memory: bool = True,
            children: typing.Optional[typing.List[py_trees.behaviour.Behaviour]] = None,
    ):
        super().__init__(name=name, memory=memory, children=children)

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(name=d['name'], memory=bool(d.get('memory', True)), children=c)

    def to_data(self):
        return {
            'memory': self.memory
        }


class Parallel(py_trees.composites.Parallel, Composite):
    def __init__(
            self,
            name: str = 'Parallel',
            policy: str = 'SuccessOnOne',  # SuccessOnOne/SuccessOnAll
            synchronise: bool = False,
            children: typing.Optional[typing.List[py_trees.behaviour.Behaviour]] = None,
    ):
        if policy == 'SuccessOnOne':
            p = py_trees.common.ParallelPolicy.SuccessOnOne()
        elif policy == 'SuccessOnAll':
            p = py_trees.common.ParallelPolicy.SuccessOnAll(synchronise=synchronise)
        else:
            p = py_trees.common.ParallelPolicy.SuccessOnOne()
        super().__init__(name=name, policy=p, children=children)

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(name=d['name'],
                   policy=d.get('policy', 'SuccessOnOne'),
                   synchronise=bool(d.get('synchronise', False)),
                   children=c)

    def to_data(self):
        return {
            'policy'     : self.policy.__class__.__name__,
            'synchronise': self.policy.synchronise
        }


class Selector(py_trees.composites.Selector, Composite):
    def __init__(
            self,
            name: str = 'Selector',
            memory: bool = True,
            children: typing.Optional[typing.List[py_trees.behaviour.Behaviour]] = None,
    ):
        super().__init__(name, children)
        self.memory = memory

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(name=d['name'], memory=bool(d.get('memory', True)), children=c)

    def to_data(self):
        return {
            'memory': self.memory
        }


class Inverter(py_trees.decorators.Inverter, Decorator):
    def __init__(self, child: py_trees.behaviour.Behaviour, name: str = 'Inverter'):
        super().__init__(name=name, child=child)

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(name=d['name'], child=c[0])


class Action(Node, ABC):
    """
    行为节点
    """

    def __init__(self, name: str = ''):
        super().__init__(name=name)
        self.actions = Queue()

    def to_data(self):
        from pybts.utility import read_queue_without_destroying
        return { 'actions': read_queue_without_destroying(self.actions) }


class Condition(Node, ABC):
    """
    条件节点
    """

    def __init__(self, name: str = ''):
        super().__init__(name=name)
