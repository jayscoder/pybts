from __future__ import annotations

import typing

from pybts.node import Status, Success, Node
from pybts.decorators.nodes import Decorator


class Reward(Node):
    """
    奖励节点，返回的状态一直是SUCCESS
    当走到这个节点时，会将给定的奖励累计

    只会对之后的节点生效，所以要放在前面
    """

    def __init__(self, reward: str | float, scope: str = 'default', **kwargs):
        super().__init__(**kwargs)
        self.reward = reward
        self.scope = scope

    def setup(self, **kwargs: typing.Any) -> None:
        super().setup(**kwargs)
        self.reward = self.converter.float(self.reward)
        self.scope = self.converter.render(self.scope).split(',')  # 域，只会将奖励保存在对应的scope中

    def update(self) -> Status:
        if self.context is not None:
            for sc in self.scope:
                self.context['rl_reward'][sc] += self.reward
        return Status.SUCCESS


class ConditionReward(Decorator):
    """
    强化学习奖励装饰节点
    根据子节点的状态来提供奖励

    success: 子节点成功时给的奖励
    failure: 子节点失败时给的奖励
    running: 子节点运行时给的奖励
    only_on_status_change: 只有在子节点的状态改变时才会提供奖励
    """

    def __init__(self,
                 scope: str = 'default',
                 success: float | str = 1, failure: float | str = 0, running: float | str = 0.5,
                 only_on_status_change: bool | str = False, **kwargs):
        super().__init__(**kwargs)
        self.success = success
        self.failure = failure
        self.running = running
        self.only_on_status_change = only_on_status_change
        self.scope = scope

        self.reward = 0  # 单次奖励
        self.accum_reward = 0  # 累积奖励

    def reset(self):
        super().reset()
        self.reward = 0
        self.accum_reward = 0

    def to_data(self):
        return {
            **super().to_data(),
            'scope'                : self.scope,
            'success'              : self.success,
            'failure'              : self.failure,
            'running'              : self.running,
            'only_on_status_change': self.only_on_status_change,
            'reward'               : self.reward,
            'accum_reward'         : self.accum_reward,
            'context'              : self.context
        }

    def setup(self, **kwargs: typing.Any) -> None:
        super().setup(**kwargs)
        self.success = self.converter.float(self.success)
        self.failure = self.converter.float(self.failure)
        self.running = self.converter.float(self.running)
        self.only_on_status_change = self.converter.bool(self.only_on_status_change)
        self.scope = self.converter.render(self.scope).split(',')  # 域，只会将奖励保存在对应的scope中

    def update(self) -> Status:
        new_status = self.decorated.status
        new_reward = 0
        if new_status == self.status and self.only_on_status_change:
            self.reward = new_reward
            return new_status

        elif new_status == Status.SUCCESS:
            new_reward = self.success
        elif new_status == Status.RUNNING:
            new_reward = self.running
        elif new_status == Status.FAILURE:
            new_reward = self.failure
        self.reward = new_reward
        self.accum_reward += new_reward

        if self.context is not None:
            for sc in self.scope:
                self.context['rl_reward'][sc] += self.reward

        return new_status


if __name__ == '__main__':
    node = ConditionReward(scope='a,b,c', success='{{1}}/10', children=[Success()])
    node.setup()
    print(node.success)
    print(node.update())
