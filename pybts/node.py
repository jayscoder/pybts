from __future__ import annotations
from abc import ABC
from queue import Queue

from py_trees import behaviour, common
from py_trees.behaviour import Behaviour

from pybts.constants import *
import typing
import py_trees
import itertools


class Node(py_trees.behaviour.Behaviour, ABC):
    """
    Base class for all nodes in the behavior tree

    被唤起的生命周期：
    如果被tick到了

    状态为RUNNING

    - initialise
    - update

    如果update之后状态从RUNNING变更为SUCCESS/FAILURE/INVALID
    - stop

    下一次tick的时候状态一开始是RUNNING，则直接调用
    update
    """

    def __init__(self, name: str = '', children: typing.List[py_trees.behaviour.Behaviour] = None, **kwargs):
        super().__init__(name=name or self.__class__.__name__)
        self._updater_iter = None
        self.debug_info = {
            'tick_count'      : 0,
            'update_count'    : 0,
            'reset_count'     : 0,
            'terminate_count' : 0,
            'initialise_count': 0
        }
        self.attrs: typing.Dict[str, typing.AnyStr] = kwargs  # 在builder和xml中传递的参数，会在__init__之后提供一个更完整的
        self.context: typing.Optional[dict] = None  # 共享的字典，在tree.setup的时候提供
        if children is not None:
            self.children = children
            for child in children:
                child.parent = self

    def reset(self):
        self.debug_info['reset_count'] += 1
        self._updater_iter = None
        if self.status != Status.INVALID:
            self.stop(Status.INVALID)

    @property
    def converter(self):
        from pybts.converter import Converter
        return Converter(self)

    def to_data(self):
        # 在board上查看的信息
        return {
            'debug_info': self.debug_info,
            'attrs'     : self.attrs
        }

    def update(self) -> Status:
        self.logger.debug("%s.update()" % (self.__class__.__name__))
        self.debug_info['update_count'] += 1
        if self._updater_iter is None:
            self._updater_iter = self.updater()
        new_status = Status.INVALID
        for _ in range(2):
            try:
                new_status = next(self._updater_iter)
                break
            except:
                self._updater_iter = self.updater()
        return new_status

    def updater(self) -> typing.Iterator[Status]:
        # 提出Status.RUNNING/Status.SUCCESS/Status.FAILURE 会继续运行该迭代器
        # 提出Status.INVALID会停止该迭代器

        yield Status.INVALID
        return

    def tick(self) -> typing.Iterator[Behaviour]:
        self.debug_info['tick_count'] += 1
        self.logger.debug("%s.tick()" % (self.__class__.__name__))

        if self.status != Status.RUNNING:
            # 开始的状态不是RUNNING
            self.initialise()

        # don't set self.status yet, terminate() may need to check what the current state is first
        new_status = self.update()

        if new_status != Status.RUNNING:
            self.stop(new_status)

        self.status = new_status
        yield self

    def stop(self, new_status: Status) -> None:
        """
        Stop the behaviour with the specified status.

        Args:
            new_status: the behaviour is transitioning to this new status

        This is called to bring the current round of activity for the behaviour to completion, typically
        resulting in a final status of :data:`~py_trees.common.Status.SUCCESS`,
        :data:`~py_trees.common.Status.FAILURE` or :data:`~py_trees.common.Status.INVALID`.

        .. warning::
           Users should not override this method to provide custom termination behaviour. The
           :meth:`~py_trees.behaviour.Behaviour.terminate` method has been provided for that purpose.
        """
        self.logger.debug(
                "%s.stop(%s)"
                % (
                    self.__class__.__name__,
                    "%s->%s" % (self.status, new_status)
                )
        )
        self.terminate(new_status)
        self.status = new_status
        self.iterator = self.tick()
        if new_status == Status.INVALID:
            self._updater_iter = None  # 停止updater

    def terminate(self, new_status: common.Status) -> None:
        super().terminate(new_status)
        self.logger.debug(
                "%s.terminate(%s)"
                % (
                    self.__class__.__name__,
                    "%s->%s" % (self.status, new_status)
                )
        )
        self.debug_info['terminate_count'] += 1

    def initialise(self) -> None:
        super().initialise()
        self.logger.debug("%s.initialise()" % (self.__class__.__name__))
        self.debug_info['initialise_count'] += 1

    def __str__(self):
        attrs = {
            'id': self.id.hex,
            **self.attrs,
        }

        attrs_str = ' '.join([f'{k}="{attrs[k]}"' for k in attrs if isinstance(attrs[k], str) and attrs[k]])
        if len(self.children) == 0:
            return f'<{self.name} {attrs_str}/>'
        else:
            return f'<{self.name} {attrs_str}/>({len(self.children)})'

    def __repr__(self):
        return self.__str__()

    def get_time(self) -> float:
        """获取行为树时间，时间可以由context传入，可以是一个函数"""
        if self.context is not None and 'time' in self.context:
            if callable(self.context['time']):
                return self.context['time']()
            # 在context传递了time的情况下使用context里的时间，方便使用游戏时间
            return self.context['time']
        else:
            import time
            return time.monotonic()


class Action(Node, ABC):
    """
    行为节点
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.actions = Queue()

    def to_data(self):
        from pybts.utility import read_queue_without_destroying
        actions = read_queue_without_destroying(self.actions)
        return {
            **super().to_data(),
            'actions': [str(act) for act in actions]
        }


class Condition:
    """
    条件节点，只能多继承使用
    """

    def condition_score(self) -> float:
        """条件达成分数，后面可以作为奖励函数设计使用"""
        if isinstance(self, Node):
            if self.status == Status.SUCCESS:
                return 1
            elif self.status == Status.RUNNING:
                return 0.5
            else:
                return 0
        return 0


class Success(Node, Condition):
    """
    成功节点
    """

    def update(self) -> Status:
        super().update()
        return Status.SUCCESS

    def stop(self, new_status: common.Status) -> None:
        super().stop(new_status)


class Failure(Node, Condition):
    """
    失败节点
    """

    def update(self) -> Status:
        super().update()
        return Status.FAILURE


class Running(Node, Condition):
    """Running Node"""

    def update(self) -> Status:
        super().update()
        return Status.RUNNING


class IsMatchRule(Node, Condition):
    """
    是否匹配预设的规则

    rule: 用python和jinja2语法描述的规定，例如{{agent.x}} > 10，返回值必须得是bool
    - 花括号里定义的变量可以从context里找到
    """

    def __init__(self, rule: str, **kwargs):
        super().__init__(**kwargs)
        self.rule = rule

    def update(self) -> Status:
        rule_value = eval(self.converter.render(self.rule))
        if rule_value:
            return Status.SUCCESS
        return Status.FAILURE


class IsChanged(Node, Condition):
    """
    value是否发生变化
    value的值从context里找，所以需要在tree每次更新时将对应的context填充进去
    返回的Status：
    - SUCCESS：发生变化
    - FAILURE：没有发生变化

    参数：
    value: 监听的值
    immediate: 是否一开始就认为发生了变化
    rule: 判断规则，默认的规则是 curr_value != last_value，可以自定义新的规则，例如 abs(curr_value - last_value) >= 10，需要确保rule返回的值是bool类型
        - rule里面也可以使用模版语法，比如 abs(curr_value - last_value) >= {{min_value}}，模版语法里的min_value需要提前在context里定义好，不然会报错
    用法示例：
    <IsChanged value="{{agent.x}}" immediate="true">
    <IsChanged value="{{agent.y}}" immediate="false" rule="abs(curr_value - last_value) >= 10">
    """

    def __init__(self, value: str, immediate: bool | str = False, rule: str = '', **kwargs):
        super().__init__(**kwargs)
        self.value = value  # 监听的值
        self.immediate = immediate
        self.last_value = None  # 上一次的值
        self.curr_value = None  # 当前值
        self.changed_count = 0  # 改变次数
        self.rule = rule  # 默认是 curr_value != last_value

    def setup(self, **kwargs: typing.Any) -> None:
        super().setup(**kwargs)
        self.immediate = self.converter.bool(self.immediate)

    def reset(self):
        super().reset()
        self.last_value = None
        self.curr_value = None
        self.changed_count = 0

    @property
    def is_changed(self):
        if self.rule == '':
            return self.curr_value != self.last_value
        else:
            rule = self.converter.render(self.rule)
            is_changed_value = eval(rule, {
                **(self.context or { }),
                'curr_value': self.curr_value,
                'last_value': self.last_value
            })
            assert isinstance(is_changed_value, bool), 'IsChanged: invalid rule'
            return is_changed_value

    def update(self) -> Status:
        self.curr_value = self.converter.render(self.value)
        if not self.immediate and self.last_value is None:
            # 刚开始不触发
            self.last_value = self.curr_value

        if self.is_changed:
            # 发生了变化
            self.changed_count += 1
            self.last_value = self.curr_value
            return Status.SUCCESS
        else:
            # 没有发生变化
            return Status.FAILURE

    def to_data(self):
        return {
            **super().to_data(),
            "immediate"    : self.immediate,
            "last_value"   : self.last_value,
            "curr_value"   : self.curr_value,
            'changed_count': self.changed_count,
            'is_changed'   : self.is_changed
        }


class Print(Action):
    def __init__(self, msg: str, **kwargs):
        super().__init__(**kwargs)
        self.msg = msg

    def update(self) -> Status:
        print(self.converter.render(self.msg))
        return Status.SUCCESS

    def to_data(self):
        return {
            **super().to_data(),
            "msg": self.converter.render(self.msg)
        }

