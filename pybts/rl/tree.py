import typing

from py_trees import common, visitors

from pybts.tree import Tree
import py_trees
import gymnasium as gym


class RLTree(Tree):
    def __init__(self, root: py_trees.behaviour.Behaviour, name: str = ''):
        super().__init__(root=root)
        self.name = name or root.name
        self.round = 0  # 第几轮

    def setup(
            self,
            env: gym.Env,
            timeout: typing.Union[float, common.Duration] = common.Duration.INFINITE,
            visitor: typing.Optional[visitors.VisitorBase] = None,
            **kwargs,
    ):
        super().setup(timeout=timeout, visitor=visitor, env=env, **kwargs)

