from __future__ import annotations

import typing

from py_trees.trees import BehaviourTree

from pybts.tree import Tree
import py_trees
from pybts.node import Node
from collections import defaultdict


class RLTree(Tree):
    """
    强化学习树
    """

    def __init__(self, root: Node, name: str = '', context: dict = None):
        super().__init__(root=root, name=name, context=context)
        self.context['rl_reward'] = defaultdict(int)  # 本轮的奖励，默认scope是default

    def reset(self):
        super().reset()
        # 清空奖励
        self.context['rl_reward'] = defaultdict(int)

    def tick(
            self: RLTree,
            pre_tick_handler: typing.Optional[
                typing.Callable[[RLTree], None]
            ] = None,
            post_tick_handler: typing.Optional[
                typing.Callable[[RLTree], None]
            ] = None,
    ) -> None:
        # 不清空奖励，由PPO节点自行判断
        # for scope in self.context['rl_reward']:
        #     self.context['rl_reward'][scope] = 0  # 在tick之前清空奖励
        super().tick(pre_tick_handler=pre_tick_handler, post_tick_handler=post_tick_handler)
