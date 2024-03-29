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
    """
    composite base class node
    """

    def __init__(
            self,
            name: str = 'Composite',
            children: typing.Optional[typing.List[py_trees.behaviour.Behaviour]] = None,
    ):
        super().__init__(name=name, children=children)


class Decorator(py_trees.decorators.Decorator, Node, ABC):
    """
    decorator base class node
    """

    def __init__(self, child: py_trees.behaviour.Behaviour, name: str = 'Decorator'):
        super().__init__(name=name, child=child)


class Sequence(py_trees.composites.Sequence, Composite):
    """
    sequence base class node
    """

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


class Parallel(Composite):
    """
    A parallel ticks every child every time the parallel is itself ticked.
    """

    def __init__(
            self,
            name: str = 'Parallel',
            success_threshold: int = 1,  # 成功的节点个数（大于等于这个数量才会认为并行节点成功，-1表示全部）
            children: typing.Optional[typing.List[py_trees.behaviour.Behaviour]] = None,
    ):
        super().__init__(name=name, children=children)
        self.success_threshold = success_threshold
        assert self.success_threshold >= -1, "success_threshold is not valid"

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(name=d['name'],
                   success_threshold=int(d.get('success_threshold', 1)),
                   children=c)

    def tick(self) -> typing.Iterator[py_trees.behaviour.Behaviour]:
        """
        Tick over the children.

        Yields:
            :class:`~py_trees.behaviour.Behaviour`: a reference to itself or one of its children

        Raises:
            RuntimeError: if the policy configuration was invalid
        """
        self.logger.debug("%s.tick()" % self.__class__.__name__)

        # reset
        if self.status != Status.RUNNING:
            self.logger.debug("%s.tick(): re-initialising" % self.__class__.__name__)
            for child in self.children:
                # reset the children, this ensures old SUCCESS/FAILURE status flags
                # don't break the synchronisation logic below
                if child.status != Status.INVALID:
                    child.stop(Status.INVALID)
            self.current_child = None
            # subclass (user) handling
            self.initialise()

        # nothing to do
        if not self.children:
            self.current_child = None
            self.stop(Status.SUCCESS)
            yield self
            return

        # process them all first
        for child in self.children:
            for node in child.tick():
                yield node

        # determine new status
        new_status = Status.RUNNING
        self.current_child = self.children[-1]
        successful = [
            child
            for child in self.children
            if child.status == Status.SUCCESS
        ]
        threshold = self.success_threshold
        if threshold == -1:
            threshold = len(self.children)

        if len(successful) >= threshold:
            new_status = Status.SUCCESS
        else:
            new_status = Status.FAILURE
        # this parallel may have children that are still running
        # so if the parallel itself has reached a final status, then
        # these running children need to be terminated so they don't dangle
        if new_status != Status.RUNNING:
            self.stop(new_status)
        self.status = new_status
        yield self

    def stop(self, new_status: Status = Status.INVALID) -> None:
        """
        Ensure that any running children are stopped.

        Args:
            new_status : the composite is transitioning to this new status
        """
        self.logger.debug(
                f"{self.__class__.__name__}.stop()[{self.status}->{new_status}]"
        )

        # clean up dangling (running) children
        for child in self.children:
            if child.status == Status.RUNNING:
                # this unfortunately knocks out it's running status for introspection
                # but logically is the correct thing to do, see #132.
                child.stop(Status.INVALID)
        Composite.stop(self, new_status)

    def to_data(self):
        return {
            'success_threshold': self.success_threshold
        }


class Selector(py_trees.composites.Selector, Composite):
    """
    Selectors are the decision makers.
    A selector executes each of its child behaviours in turn until one of them succeeds
    """

    def __init__(
            self,
            name: str = 'Selector',
            memory: bool = True,
            children: typing.Optional[typing.List[py_trees.behaviour.Behaviour]] = None,
    ):
        super().__init__(name=name, memory=memory, children=children)
        self.memory = memory

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(name=d['name'], memory=bool(d.get('memory', True)), children=c)

    def to_data(self):
        return {
            'memory': self.memory
        }


class Inverter(py_trees.decorators.Inverter, Decorator):
    """A decorator that inverts the result of a class's update function."""

    def __init__(self, child: py_trees.behaviour.Behaviour, name: str = 'Inverter'):
        super().__init__(name=name, child=child)

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(name=d['name'], child=c[0])


class Action(Node, ABC):
    """
    行为节点
    """
    meta = {
        'desc': '行为节点'
    }

    def __init__(self, name: str = ''):
        super().__init__(name=name)
        self.actions = Queue()

    def to_data(self):
        from pybts.utility import read_queue_without_destroying
        actions = read_queue_without_destroying(self.actions)
        return { 'actions': [str(act) for act in actions] }


class Condition(Node, ABC):
    """
    条件节点
    """
    meta = {
        'desc': '条件节点'
    }

    def __init__(self, name: str = ''):
        super().__init__(name=name)
