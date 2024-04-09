from __future__ import annotations

from pybts.builder import Builder
from pybts.rl.nodes import Reward, ConditionReward


class RLBuilder(Builder):
    def register_default(self):
        super().register_default()
        self.register_node(Reward, ConditionReward)
