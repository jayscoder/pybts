from __future__ import annotations
from abc import ABC
from queue import Queue

from py_trees import behaviour, common
from py_trees.behaviour import Behaviour

from pybts.constants import *
import typing
import py_trees
import itertools
import random


class Node(py_trees.behaviour.Behaviour, ABC):
    """
    Base class for all nodes in the behavior tree

    被唤起的生命周期：
    - setup 只会执行一次

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
        self.attrs: typing.Dict[str, typing.AnyStr] = kwargs or { }  # 在builder和xml中传递的参数，会在__init__之后提供一个更完整的
        self.context: typing.Optional[dict] = None  # 共享的字典，在tree.setup的时候提供，所以不要在__init__的时候修改或使用它，而是在setup的时候使用
        super().__init__(name=name or self.__class__.__name__)
        self._updater_iter = None
        self.debug_info = {
            'tick_count'      : 0,
            'update_count'    : 0,
            'reset_count'     : 0,
            'terminate_count' : 0,
            'initialise_count': 0
        }
        if children is not None:
            self.children = children
            for child in children:
                child.parent = self

    def setup(self, **kwargs: typing.Any) -> None:
        super().setup(**kwargs)
        self.name = self.converter.render(self.name)

    def reset(self):
        self.debug_info['reset_count'] += 1
        self._updater_iter = None
        if self.status != Status.INVALID:
            self.stop(Status.INVALID)

    @property
    def label(self):
        if 'label' in self.attrs:
            return self.converter.render(self.attrs['label'])
        return self.name

    @property
    def converter(self):
        from pybts.converter import Converter
        return Converter(self)

    def to_data(self):
        # 在board上查看的信息
        return {
            'debug_info': self.debug_info,
            'attrs'     : self.attrs,
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
            except StopIteration:
                self._updater_iter = self.updater()
        assert isinstance(new_status, Status), f'{self.name}: {new_status} is not a valid status'
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
        assert isinstance(new_status, Status), f'{self.name}: {new_status} is not a valid status'
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

    def get_time(self, time: str | float) -> float:
        """获取行为树时间，时间可以由context传入，可以是一个函数"""
        if time == 'time':
            import time
            return time.monotonic()
        return self.converter.float(time)


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

    <IsChanged value="{{agent.y}}" immediate="false" rule="abs(curr_value - last_value) >= 10">

    <Sequence>
        <IsChanged value="{{agent.hit_enemy_count}}" immediate="false">
        <Reward reward="1" domain="attack"/>
    </Sequence>
    """

    def __init__(self, value: typing.Any, immediate: bool | str = False, rule: str = '', **kwargs):
        super().__init__(**kwargs)
        self.value = value  # 监听的值
        self.immediate = immediate
        self.last_value = None  # 上一次的值
        self.curr_value = None
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

    def check_is_changed(self, curr_value: typing.Any, last_value: typing.Any):
        if self.rule == '':
            return curr_value != last_value
        else:
            rule = self.converter.render(self.rule)
            is_changed_value = eval(rule, {
                **(self.context or { }),
                'curr_value'   : curr_value,
                'last_value'   : last_value,
                'changed_count': self.changed_count
            })
            assert isinstance(is_changed_value, bool), 'IsChanged: invalid rule'
            return is_changed_value

    def compute_curr_value(self):
        if isinstance(self.value, str):
            return self.converter.render(self.value)
        else:
            return self.value

    def update(self) -> Status:
        self.curr_value = self.compute_curr_value()
        if not self.immediate and self.last_value is None:
            # 刚开始不触发
            self.last_value = self.curr_value

        is_changed = self.check_is_changed(curr_value=self.curr_value, last_value=self.last_value)

        self.logger.debug(f'{self.last_value} -> {self.curr_value}: {is_changed}')

        self.last_value = self.curr_value
        if is_changed:
            # 发生了变化
            self.changed_count += 1
            return Status.SUCCESS
        else:
            # 没有发生变化
            return Status.FAILURE

    def to_data(self):
        return {
            **super().to_data(),
            "immediate"    : self.immediate,
            "last_value"   : self.last_value,
            'curr_value'   : self.curr_value,
            'changed_count': self.changed_count,
        }


class IsEqual(Node, Condition):
    """
    检查两个值是否相等，值本身可以从context中拿到
    """

    def __init__(self, a: str, b: str, **kwargs):
        super().__init__(**kwargs)
        self.a = a
        self.b = b

        self.curr_a = None
        self.curr_b = None

    def to_data(self):
        return {
            **super().to_data(),
            'curr_a': self.curr_a,
            'curr_b': self.curr_b
        }

    def reset(self):
        super().reset()
        self.curr_a = None
        self.curr_b = None

    def update(self):
        self.curr_a = self.converter.render(self.a)
        self.curr_b = self.converter.render(self.b)
        if self.curr_a == self.curr_b:
            return Status.SUCCESS
        else:
            return Status.FAILURE


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


class RandomIntValue(Node):
    """
    生成随机整数到context里

    随机数范围: [low, high], including both end points.
    """

    def __init__(self, key: str, high: int | str, low: int | str = 0, **kwargs):
        super().__init__(**kwargs)
        self.high = high
        self.low = low
        self.key = key
        self.value = None

    def setup(self, **kwargs: typing.Any) -> None:
        super().setup(**kwargs)
        self.key = self.converter.render(self.key)

    def update(self) -> Status:
        low = self.converter.int(self.low)
        high = self.converter.int(self.high)

        self.value = random.randint(low, high)
        self.context[self.key] = self.value
        return Status.SUCCESS

    def to_data(self):
        return {
            **super().to_data(),
            'key'  : self.key,
            'value': self.value
        }


class RandomFloatValue(Node):
    """
    生成随机浮点数到context里

    随机数范围: [low, high), 不包括high
    """

    def __init__(self, key: str, high: float | str = 1, low: float | str = 0, **kwargs):
        super().__init__(**kwargs)
        self.high = high
        self.low = low
        self.key = key
        self.value = None

    def setup(self, **kwargs: typing.Any) -> None:
        super().setup(**kwargs)
        self.key = self.converter.render(self.key)

    def update(self) -> Status:
        low = self.converter.float(self.low)
        high = self.converter.float(self.high)

        self.value = random.random() * (high - low) + low
        self.context[self.key] = self.value
        return Status.SUCCESS

    def to_data(self):
        return {
            **super().to_data(),
            'key'  : self.key,
            'value': self.value
        }


class RandomSuccess(Node, Condition):
    """
    以一定概率成功，其他情况是失败
    """

    def __init__(self, prob: float | str = 0.5, **kwargs):
        super().__init__(**kwargs)
        self.prob = prob
        self.curr_prob = None

    def to_data(self):
        return {
            **super().to_data(),
            'curr_prob': self.curr_prob
        }

    def update(self) -> Status:
        self.curr_prob = self.converter.float(self.prob)
        assert 0 <= self.curr_prob <= 1, "Probability must be between 0 and 1"
        if random.random() < self.curr_prob:
            return Status.SUCCESS
        return Status.FAILURE


class SetValueToContext(Node):
    def __init__(self, key: str, value: typing.Any, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self.value = value
        self.curr_value = None

    def setup(self, **kwargs: typing.Any) -> None:
        super().__init__(**kwargs)
        self.key = self.converter.render(self.key)

    def to_data(self):
        return {
            **super().to_data(),
            'key'       : self.key,
            'curr_value': self.curr_value
        }

    def compute_curr_value(self) -> typing.Any:
        return self.converter.render(self.value)

    def update(self) -> Status:
        self.curr_value = self.compute_curr_value()
        self.context[self.key] = self.curr_value
        return Status.SUCCESS


class SetIntToContext(SetValueToContext):
    def compute_curr_value(self) -> typing.Any:
        return self.converter.int(self.value)


class SetFloatToContext(SetValueToContext):
    def compute_curr_value(self) -> typing.Any:
        return self.converter.float(self.value)


class TimeElapsed(Node, Condition):
    """
    时间是否过去了
    每隔一段时间才会触发一次子节点，其他时间直接返回之前的状态
    """

    def __init__(self, duration: float | str = 5.0, time: str | float = 'time', immediate: bool | str = False,
                 **kwargs):
        """
        Init with the decorated child and a timeout duration.

        Args:
            child: the child behaviour or subtree
            name: the decorator name
            duration: timeout length in seconds
            time: 当前时间，传time表示使用系统时间
            immediate: 一开始是否就触发一次
        """
        super().__init__(**kwargs)
        self.duration = duration
        self.immediate = immediate
        self.time = time

        self.curr_duration = None
        self.last_time = None
        self.curr_time = None

    def reset(self):
        super().reset()
        self.last_time = None
        self.curr_time = None

    def setup(self, **kwargs: typing.Any) -> None:
        super().setup(**kwargs)
        self.immediate = self.converter.bool(self.immediate)

    def to_data(self):
        return {
            **super().to_data(),
            'immediate'    : self.immediate,
            'curr_time'    : self.curr_time,
            'last_time'    : self.last_time,
            'curr_duration': self.curr_duration,
        }

    def update(self) -> Status:
        self.curr_time = self.get_time(self.time)
        self.curr_duration = self.converter.float(self.duration)

        if self.last_time is None:
            self.last_time = self.curr_time
            return Status.SUCCESS if self.immediate else Status.FAILURE

        if self.curr_time - self.last_time >= self.curr_duration:
            self.last_time = self.curr_time
            return Status.SUCCESS
        return Status.FAILURE
