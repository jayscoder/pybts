from __future__ import annotations
import py_trees
from pybts.node import Node
from abc import ABC
from py_trees.common import Status
import typing


class Decorator(Node, ABC):
    """
    装饰节点
    只有一个子节点
    """

    def __init__(self, child: py_trees.behaviour.Behaviour, **kwargs):
        # Checks
        if not isinstance(child, py_trees.behaviour.Behaviour):
            raise TypeError(
                    "A decorator's child must be an instance of py_trees.behaviours.Behaviour"
            )
        # Initialise
        super().__init__(**kwargs)
        self.children.append(child)
        # Give a convenient alias
        self.decorated = self.children[0]
        self.decorated.parent = self

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(child=c[0], **d)

    def tick(self) -> typing.Iterator[py_trees.behaviour.Behaviour]:
        """
        Manage the decorated child through the tick.

        Yields:
            a reference to itself or one of its children
        """
        self.logger.debug("%s.tick()" % self.__class__.__name__)
        # initialise just like other behaviours/composites
        if self.status != Status.RUNNING:
            self.initialise()
        # interrupt proceedings and process the child node
        # (including any children it may have as well)
        for node in self.decorated.tick():
            yield node
        # resume normal proceedings for a Behaviour's tick
        new_status = self.update()
        if new_status not in list(Status):
            self.logger.error(
                    "A behaviour returned an invalid status, setting to INVALID [%s][%s]"
                    % (new_status, self.name)
            )
            new_status = Status.INVALID
        if new_status != Status.RUNNING:
            self.stop(new_status)
        self.status = new_status
        yield self

    def stop(self, new_status: Status) -> None:
        """
        Check if the child is running (dangling) and stop it if that is the case.

        Args:
            new_status (:class:`~py_trees.Status`): the behaviour is transitioning to this new status
        """
        self.logger.debug("%s.stop(%s)" % (self.__class__.__name__, new_status))
        self.terminate(new_status)
        # priority interrupt handling
        if new_status == Status.INVALID:
            self.decorated.stop(new_status)
        # if the decorator returns SUCCESS/FAILURE and should stop the child
        if self.decorated.status == Status.RUNNING:
            self.decorated.stop(Status.INVALID)
        self.status = new_status

    def tip(self) -> typing.Optional[py_trees.behaviour.Behaviour]:
        """
        Retrieve the *tip* of this behaviour's subtree (if it has one).

        This corresponds to the the deepest node that was running before the
        subtree traversal reversed direction and headed back to this node.

        Returns:
            child behaviour, or :obj:`None` if its status is :data:`~py_trees.Status.INVALID`
        """
        if self.decorated.status != Status.INVALID:
            return self.decorated.tip()
        else:
            return super().tip()


class Inverter(Decorator):
    """
    装饰节点：取反
    - SUCCESS: 子节点返回失败
    - FAILURE: 子节点返回成功
    """

    def update(self) -> Status:
        """
        Flip :data:`~py_trees.Status.SUCCESS` and :data:`~py_trees.Status.FAILURE`.

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        if self.decorated.status == Status.SUCCESS:
            self.feedback_message = "success -> failure"
            return Status.FAILURE
        elif self.decorated.status == Status.FAILURE:
            self.feedback_message = "failure -> success"
            return Status.SUCCESS
        self.feedback_message = self.decorated.feedback_message
        return self.decorated.status


class RunningUntilCondition(Decorator):
    """
    A blocking conditional decorator.

    Encapsulates a behaviour and wait for it's status to flip to the
    desired state. This behaviour will tick with
    :data:`~py_trees.Status.RUNNING` while waiting and
    :data:`~py_trees.Status.SUCCESS` when the flip occurs.
    """

    def __init__(self, child: py_trees.behaviour.Behaviour, status: str | Status, **kwargs):
        """
        Initialise with child and optional name, status variables.

        Args:
            name: the decorator name
            child: the child to be decorated
            status: the desired status to watch for
        """
        super().__init__(child=child, **kwargs)
        if isinstance(status, str):
            status = Status(status)
        self.succeed_status = status

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(
                child=c[0],
                **d
        )

    def to_data(self):
        return {
            **super().to_data(),
            'succeed_status': self.succeed_status
        }

    def update(self) -> Status:
        """
        Check if the condtion has triggered, block otherwise.

        :data:`~py_trees.Status.SUCCESS` if the decorated child has returned
        the specified status, otherwise :data:`~py_trees.Status.RUNNING`.
        This decorator will never return :data:`~py_trees.Status.FAILURE`

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        self.logger.debug("%s.update()" % self.__class__.__name__)
        self.feedback_message = (
            f"'{self.decorated.name}' has status {self.decorated.status}, "
            f"waiting for {self.succeed_status}"
        )
        if self.decorated.status == self.succeed_status:
            return Status.SUCCESS
        return Status.RUNNING


class OneShot(Decorator):
    """
    A decorator that implements the oneshot pattern.

    This decorator ensures that the underlying child is ticked through
    to completion just once and while doing so, will return
    with the same status as it's child. Thereafter it will return
    with the final status of the underlying child.

    Completion status is determined by the policy given on construction.

    * With policy :data:`~py_trees.common.OneShotPolicy.ON_SUCCESSFUL_COMPLETION`, the oneshot will activate
      only when the underlying child returns :data:`~py_trees.Status.SUCCESS` (i.e. it permits retries).
    * With policy :data:`~py_trees.common.OneShotPolicy.ON_COMPLETION`, the oneshot will activate when the child
      returns :data:`~py_trees.Status.SUCCESS` || :data:`~py_trees.Status.FAILURE`.

    .. seealso:: :meth:`py_trees.idioms.oneshot`
    """

    def __init__(
            self, child: py_trees.behaviour.Behaviour, policy: str | list[Status] = 'SUCCESS', **kwargs
    ):
        """
        Init with the decorated child.

        Args:
            child: behaviour to shoot
            name: the decorator name
            policy: policy determining when the oneshot should activate
            - SUCCESS
            - SUCCESS|FAILURE
        """
        super(OneShot, self).__init__(child=child, **kwargs)
        self.final_status: typing.Optional[Status] = None
        if isinstance(policy, str):
            self.policy = list(map(lambda x: Status(x), policy.split('|')))
        else:
            self.policy = policy

    @classmethod
    def creator(cls, d: dict, c: list):
        return cls(
                child=c[0],
                **d
        )

    def to_data(self):
        return {
            **super().to_data(),
            'policy'      : self.policy,
            'final_status': self.final_status
        }

    def update(self) -> Status:
        """
        Bounce if the child has already successfully completed.

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        if self.final_status:
            self.logger.debug("{}.update()[bouncing]".format(self.__class__.__name__))
            return self.final_status
        return self.decorated.status

    def tick(self) -> typing.Iterator[py_trees.behaviour.Behaviour]:
        """
        Tick the child or bounce back with the original status if already completed.

        Yields:
            a reference to itself or a behaviour in it's child subtree
        """
        if self.final_status:
            # ignore the child
            for node in py_trees.behaviour.Behaviour.tick(self):
                yield node
        else:
            # tick the child
            for node in Decorator.tick(self):
                yield node

    def terminate(self, new_status: Status) -> None:
        """
        Prevent further entry if finishing with :data:`~py_trees.Status.SUCCESS`.

        This uses a flag to register that the behaviour has gone through to completion.
        In future ticks, it will block entry to the child and just return the original
        status result.
        """
        if not self.final_status and new_status in self.policy:
            self.logger.debug(
                    "{}.terminate({})[oneshot completed]".format(
                            self.__class__.__name__, new_status
                    )
            )
            self.feedback_message = "oneshot completed"
            self.final_status = new_status
        else:
            self.logger.debug(
                    "{}.terminate({})".format(self.__class__.__name__, new_status)
            )


class Count(Decorator):
    """
    Count the number of times it's child has been ticked.

    This increments counters tracking the total number of times
    it's child has been ticked as well as the number of times it
    has landed in each respective state.

    It will always re-zero counters on
    :meth:`~py_trees.behaviour.Behaviour.setup`.

    Attributes:
        total_tick_count: number of ticks in total
        running_count: number of ticks resulting in this state
        success_count: number of ticks resulting in this state
        failure_count: number of ticks resulting in this state
        interrupt_count: number of times a higher priority has interrupted
    """

    def __init__(self, child: py_trees.behaviour.Behaviour, name: str = '', **kwargs):
        """
        Init the counter.

        Args:
            name: the decorator name
            child: the child behaviour or subtree
        """
        super(Count, self).__init__(name=name, child=child, **kwargs)
        self.total_tick_count = 0
        self.failure_count = 0
        self.success_count = 0
        self.running_count = 0
        self.interrupt_count = 0

    def to_data(self):
        return {
            **super().to_data(),
            'total_tick_count': self.total_tick_count,
            'failure_count'   : self.failure_count,
            'success_count'   : self.success_count,
            'running_count'   : self.running_count,
            'interrupt_count' : self.interrupt_count
        }

    def setup(self, **kwargs: int) -> None:
        """Reset the counters."""
        self.total_tick_count = 0
        self.failure_count = 0
        self.running_count = 0
        self.success_count = 0
        self.interrupt_count = 0

    def update(self) -> Status:
        """
        Increment the counter.

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        self.logger.debug("%s.update()" % (self.__class__.__name__))
        self.total_tick_count += 1
        if self.decorated.status == Status.RUNNING:
            self.running_count += 1
        return self.decorated.status

    def terminate(self, new_status: Status) -> None:
        """Increment the completion / interruption counters."""
        self.logger.debug(
                "%s.terminate(%s->%s)" % (self.__class__.__name__, self.status, new_status)
        )
        if new_status == Status.INVALID:
            self.interrupt_count += 1
        elif new_status == Status.SUCCESS:
            self.success_count += 1
        elif new_status == Status.FAILURE:
            self.failure_count += 1
        sft = f"S: {self.success_count}, F: {self.failure_count}, T: {self.total_tick_count}"
        self.feedback_message = f"R: {self.running_count}, {sft}"

    def __repr__(self) -> str:
        """
        Generate a simple string representation of the object.

        Returns:
            string representation
        """
        s = "%s\n" % self.name
        s += "  Status   : %s\n" % self.status
        s += "  Running  : %s\n" % self.running_count
        s += "  Success  : %s\n" % self.success_count
        s += "  Failure  : %s\n" % self.failure_count
        s += "  Interrupt: %s\n" % self.interrupt_count
        s += "  ---------------\n"
        s += "  Total    : %s\n" % self.total_tick_count
        return s


class RunningIsFailure(Decorator):
    """Got to be snappy! We want results...yesterday."""

    def update(self) -> Status:
        """
        Reflect :data:`~py_trees.Status.RUNNING` as :data:`~py_trees.Status.FAILURE`.

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        if self.decorated.status == Status.RUNNING:
            self.feedback_message = "running is failure" + (
                " [%s]" % self.decorated.feedback_message
                if self.decorated.feedback_message
                else ""
            )
            return Status.FAILURE
        else:
            self.feedback_message = self.decorated.feedback_message
            return self.decorated.status


class RunningIsSuccess(Decorator):
    """Don't hang around..."""

    def update(self) -> Status:
        """
        Reflect :data:`~py_trees.Status.RUNNING` as :data:`~py_trees.Status.SUCCESS`.

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        if self.decorated.status == Status.RUNNING:
            self.feedback_message = "running is success" + (
                " [%s]" % self.decorated.feedback_message
                if self.decorated.feedback_message
                else ""
            )
            return Status.SUCCESS
        self.feedback_message = self.decorated.feedback_message
        return self.decorated.status


class FailureIsSuccess(Decorator):
    """Be positive, always succeed."""

    def update(self) -> Status:
        """
        Reflect :data:`~py_trees.Status.FAILURE` as :data:`~py_trees.Status.SUCCESS`.

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        if self.decorated.status == Status.FAILURE:
            self.feedback_message = "failure is success" + (
                " [%s]" % self.decorated.feedback_message
                if self.decorated.feedback_message
                else ""
            )
            return Status.SUCCESS
        self.feedback_message = self.decorated.feedback_message
        return self.decorated.status


class FailureIsRunning(Decorator):
    """Dont stop running."""

    def update(self) -> Status:
        """
        Reflect :data:`~py_trees.Status.FAILURE` as :data:`~py_trees.Status.RUNNING`.

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        if self.decorated.status == Status.FAILURE:
            self.feedback_message = "failure is running" + (
                " [%s]" % self.decorated.feedback_message
                if self.decorated.feedback_message
                else ""
            )
            return Status.RUNNING
        self.feedback_message = self.decorated.feedback_message
        return self.decorated.status


class SuccessIsFailure(Decorator):
    """Be depressed, always fail."""

    def update(self) -> Status:
        """
        Reflect :data:`~py_trees.Status.SUCCESS` as :data:`~py_trees.Status.FAILURE`.

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        if self.decorated.status == Status.SUCCESS:
            self.feedback_message = "success is failure" + (
                " [%s]" % self.decorated.feedback_message
                if self.decorated.feedback_message
                else ""
            )
            return Status.FAILURE
        self.feedback_message = self.decorated.feedback_message
        return self.decorated.status


class SuccessIsRunning(Decorator):
    """The tickling never ends..."""

    def update(self) -> Status:
        """
        Reflect :data:`~py_trees.Status.SUCCESS` as :data:`~py_trees.Status.RUNNING`.

        Returns:
            the behaviour's new status :class:`~py_trees.Status`
        """
        if self.decorated.status == Status.SUCCESS:
            self.feedback_message = (
                    "success is running [%s]" % self.decorated.feedback_message
            )
            return Status.RUNNING
        self.feedback_message = self.decorated.feedback_message
        return self.decorated.status
