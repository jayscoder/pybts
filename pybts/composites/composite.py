from __future__ import annotations
import py_trees
from pybts.nodes import Node
from abc import ABC
import typing
from py_trees.common import Status
from py_trees import behaviour
import itertools
import uuid


class Composite(Node, ABC):
    """
    组合节点
    """

    def __init__(
            self,
            children: typing.Optional[typing.List[py_trees.behaviour.Behaviour]] = None,
            **kwargs
    ):
        super().__init__(children=children, **kwargs)
        self.current_child: typing.Optional[behaviour.Behaviour] = None

    def stop(self, new_status: Status = Status.INVALID) -> None:
        """
        Provide common stop-level functionality for all composites.

         * Retain the current child on :data:`~py_trees.common.Status.SUCCESS` or
           :data:`~py_trees.common.Status.FAILURE` (for introspection), lose it on
           :data:`~py_trees.common.Status.INVALID`
         * Kill dangling (:data:`~py_trees.common.Status.RUNNING`) children

        The latter situation can arise for some composites, but more importantly,
        will always occur when high higher priority behaviour interrupts this one.

        Args:
            new_status: behaviour will transition to this new status
        """
        self.logger.debug(
                "%s.stop(%s)"
                % (
                    self.__class__.__name__,
                    "%s->%s" % (self.status, new_status)
                )
        )
        # Priority interrupt handling
        if new_status == Status.INVALID:
            self.current_child = None
            for child in self.children:
                if (
                        child.status != Status.INVALID
                ):  # redundant if INVALID->INVALID
                    child.stop(new_status)

        # Regular Behaviour.stop() handling
        #   could call directly, but replicating here to avoid repeating the logger
        self.terminate(new_status)
        self.status = new_status
        self.iterator = self.tick()

    def tip(self) -> typing.Optional[behaviour.Behaviour]:
        """
        Recursive function to extract the last running node of the tree.

        Returns:
            the tip function of the current child of this composite or None
        """
        if self.current_child is not None:
            return self.current_child.tip()
        else:
            return super().tip()

        ############################################
        # Children
        ############################################

    def add_child(self, child: behaviour.Behaviour) -> uuid.UUID:
        """
        Add a child.

        Args:
            child: child to add

        Raises:
            TypeError: if the child is not an instance of :class:`~py_trees.behaviour.Behaviour`
            RuntimeError: if the child already has a parent

        Returns:
            unique id of the child
        """
        if not isinstance(child, behaviour.Behaviour):
            raise TypeError(
                    "children must be behaviours, but you passed in {}".format(type(child))
            )
        self.children.append(child)
        if child.parent is not None:
            raise RuntimeError(
                    "behaviour '{}' already has parent '{}'".format(
                            child.name, child.parent.name
                    )
            )
        child.parent = self
        return child.id

    def add_children(
            self, children: typing.List[behaviour.Behaviour]
    ) -> behaviour.Behaviour:
        """
        Append a list of children to the current list.

        Args:
            children ([:class:`~py_trees.behaviour.Behaviour`]): list of children to add
        """
        for child in children:
            self.add_child(child)
        return self

    def remove_child(self, child: behaviour.Behaviour) -> int:
        """
        Remove the child behaviour from this composite.

        Args:
            child: child to delete

        Returns:
            index of the child that was removed

        .. todo:: Error handling for when child is not in this list
        """
        if self.current_child is not None and (self.current_child.id == child.id):
            self.current_child = None
        if child.status == Status.RUNNING:
            child.stop(Status.INVALID)
        child_index = self.children.index(child)
        self.children.remove(child)
        child.parent = None
        return child_index

    def remove_all_children(self) -> None:
        """Remove all children. Makes sure to stop each child if necessary."""
        self.current_child = None
        for child in self.children:
            if child.status == Status.RUNNING:
                child.stop(Status.INVALID)
            child.parent = None
        # makes sure to delete it for this class and all references to it
        #   http://stackoverflow.com/questions/850795/clearing-python-lists
        del self.children[:]

    def replace_child(
            self, child: behaviour.Behaviour, replacement: behaviour.Behaviour
    ) -> None:
        """
        Replace the child behaviour with another.

        Args:
            child: child to delete
            replacement: child to insert
        """
        self.logger.debug(
                "%s.replace_child()[%s->%s]"
                % (self.__class__.__name__, child.name, replacement.name)
        )
        child_index = self.children.index(child)
        self.remove_child(child)
        self.insert_child(replacement, child_index)
        child.parent = None

    def remove_child_by_id(self, child_id: uuid.UUID) -> None:
        """
        Remove the child with the specified id.

        Args:
            child_id: unique id of the child

        Raises:
            IndexError: if the child was not found
        """
        child = next((c for c in self.children if c.id == child_id), None)
        if child is not None:
            self.remove_child(child)
        else:
            raise IndexError(
                    "child was not found with the specified id [%s]" % child_id
            )

    def prepend_child(self, child: behaviour.Behaviour) -> uuid.UUID:
        """
        Prepend the child before all other children.

        Args:
            child: child to insert

        Returns:
            uuid.UUID: unique id of the child
        """
        self.children.insert(0, child)
        child.parent = self
        return child.id

    def insert_child(self, child: behaviour.Behaviour, index: int) -> uuid.UUID:
        """
        Insert child at the specified index.

        This simply directly calls the python list's :obj:`insert` method using the child and index arguments.

        Args:
            child (:class:`~py_trees.behaviour.Behaviour`): child to insert
            index (:obj:`int`): index to insert it at

        Returns:
            uuid.UUID: unique id of the child
        """
        self.children.insert(index, child)
        child.parent = self
        return child.id

    def seq_sel_tick(
            self,
            tick_again_status: list[Status],
            continue_status: list[Status],
            no_child_status: Status,
            start_index: int | typing.Callable[['Composite'], int] = 0
    ):
        """Sequence/Selector的tick逻辑"""
        self.debug_info['tick_count'] += 1
        self.logger.debug("%s.tick()" % (self.__class__.__name__))

        if self.status in tick_again_status:
            # 重新执行上次执行的子节点
            assert self.current_child is not None
            index = self.children.index(self.current_child)
        else:
            # Restart
            self.current_child = None  # 从头执行
            if callable(start_index):
                start_index = start_index(self)
            index = start_index

        for child in itertools.islice(self.children, index, None):
            self.current_child = child
            yield from child.tick()
            if child.status not in continue_status:
                # 不在Next里，停止执行
                break

        if self.current_child is not None:
            new_status = self.current_child.status

            index = self.children.index(self.current_child)

            # 剩余的子节点全部停止
            for child in itertools.islice(self.children, index + 1, None):
                # 清除子节点的状态（停止正在执行的子节点）
                child.stop(Status.INVALID)
        else:
            new_status = no_child_status

        # # TODO: 这里要不要加这个是存疑的（组合节点invalid stop会停止所有子节点，所以某个子节点返回invalid是否要将所有的其他节点都停止？）
        if new_status != Status.RUNNING:
            self.stop(new_status)

        self.status = new_status
        yield self

    def switch_tick(self, index: int | typing.Callable[['Composite'], int], tick_again_status: list[Status]) -> \
            typing.Iterator[py_trees.behaviour.Behaviour]:
        if self.status in tick_again_status:
            # 重新执行上次执行的子节点
            assert self.current_child is not None
        else:
            if callable(index):
                index = index(self)
            self.current_child = self.children[index]  # 执行对应的index

        yield from self.current_child.tick()
        for child in self.children:
            if child != self.current_child:
                # 清除子节点的状态（停止正在执行的子节点）
                child.stop(Status.INVALID)

        self.status = self.current_child.status
        yield self

    def gen_index(self):
        """每个组合节点都有对于这个函数的不同定义"""
        return 0

    @property
    def reactive(self) -> bool:
        return self.converter.bool(self.attrs.get('reactive', False))

    @property
    def memory(self) -> bool:
        return self.converter.bool(self.attrs.get('memory', False))

    @property
    def current_index(self):
        if self.current_child is None:
            return None
        else:
            return self.children.index(self.current_child)

    def to_data(self):
        return {
            **super().to_data(),
            'reactive'     : self.reactive,
            'memory'       : self.memory,
            'current_index': self.current_index
        }
