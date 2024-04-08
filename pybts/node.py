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

    def __init__(self, name: str = '', **kwargs):
        super().__init__(name=name or self.__class__.__name__)
        self._updater_iter = None
        self.debug_info = {
            'tick_count'      : 0,
            'update_count'    : 0,
            'reset_count'     : 0,
            'terminate_count' : 0,
            'initialise_count': 0
        }

    def reset(self):
        self.debug_info['reset_count'] += 1
        self._updater_iter = None
        if self.status != Status.INVALID:
            self.stop(Status.INVALID)

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(**d)

    def to_data(self):
        # 在board上查看的信息
        return {
            'debug_info': self.debug_info,
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
        if len(self.children) == 0:
            return f'<{self.name} id="{self.id.hex}"/>'
        else:
            return f'<{self.name} id="{self.id.hex}"> {len(self.children)} </{self.name}>'

    def __repr__(self):
        return self.__str__()


class Action(Node, ABC):
    """
    行为节点
    """

    def __init__(self, name: str = '', **kwargs):
        super().__init__(name=name, **kwargs)
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
    pass


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
