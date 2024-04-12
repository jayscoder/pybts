import typing

import py_trees
from py_trees import common, visitors
from py_trees.trees import BehaviourTree

from pybts.nodes import Node
from pybts.builder import Builder


class Tree(py_trees.trees.BehaviourTree):
    def __init__(self, root: py_trees.behaviour.Behaviour, name: str = '', context: dict = None):
        super().__init__(root=root)
        self.name = name or root.name
        self.reset_handlers: typing.List[
            typing.Callable[["Tree"], None]
        ] = []

        self.context = {
            'round': 0,
            **(context or { }),
        }  # 环境字典

        self._has_setup = False

    @property
    def round(self):
        """第几轮"""
        return self.context['round']

    @round.setter
    def round(self, value):
        self.context['round'] = value

    def setup(
            self,
            timeout: typing.Union[float, common.Duration] = common.Duration.INFINITE,
            visitor: typing.Optional[visitors.VisitorBase] = None,
            **kwargs: any,
    ) -> 'Tree':
        assert not self._has_setup, f'Tree {self.name} already has setup'
        self._has_setup = True
        for node in self.root.iterate():
            node.context = self.context
        super().setup(timeout=timeout, visitor=visitor, **kwargs)
        return self

    def reset(self):
        self.count = 0
        self.round += 1
        for node in self.root.iterate():
            if isinstance(node, Node):
                node.reset()
        for handler in self.reset_handlers:
            handler(self)

    def add_reset_handler(self, handler: typing.Callable[["Tree"], None]):
        self.reset_handlers.append(handler)

    def tick(
            self: 'Tree',
            pre_tick_handler: typing.Optional[
                typing.Callable[['Tree'], None]
            ] = None,
            post_tick_handler: typing.Optional[
                typing.Callable[['Tree'], None]
            ] = None,
    ) -> None:
        assert self._has_setup, f'Tree {self.name} has not been setup'
        super().tick(pre_tick_handler=pre_tick_handler, post_tick_handler=post_tick_handler)
