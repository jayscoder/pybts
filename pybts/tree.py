import typing

import py_trees
from py_trees import common, visitors
from pybts.node import Node


class Tree(py_trees.trees.BehaviourTree):
    def __init__(self, root: py_trees.behaviour.Behaviour, name: str = ''):
        super().__init__(root=root)
        self.name = name or root.name
        self.round = 0  # 第几轮

    def reset(self):
        self.count = 0
        self.round += 1
        for node in self.root.iterate():
            if isinstance(node, Node):
                node.reset()

