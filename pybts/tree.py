import typing

import py_trees
from py_trees import common, visitors
from pybts.node import Node
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
            builder: typing.Optional[Builder] = None,
            **kwargs: any,
    ) -> None:
        for node in self.root.iterate():
            node.context = self.context
        super().setup(timeout=timeout, visitor=visitor, builder=builder, **kwargs)

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
