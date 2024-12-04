import logging
import unittest
from pybts import *


class TestThrottle(unittest.TestCase):

    def setUp(self):
        logging.level = logging.Level.DEBUG

    class TestNode(Node):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.update_count = 0

        def update(self) -> Status:
            self.update_count += 1
            return self.status

    def test_throttle(self):
        test_node = self.TestNode()
        throttle = Throttle(
                time=0,
                duration=5,
                children=[test_node],
                policy=''
        )
        tree = Tree(root=throttle)
        tree.setup()
        test_node.status = Status.SUCCESS
        tree.tick()
        self.assertEqual(throttle.status, Status.SUCCESS)
        self.assertEqual(test_node.update_count, 1)
        throttle.time = 3
        tree.tick()
        self.assertEqual(throttle.status, Status.SUCCESS)
        self.assertEqual(test_node.update_count, 1)
        tree.tick()
        self.assertEqual(throttle.status, Status.SUCCESS)
        self.assertEqual(test_node.update_count, 1)

        throttle.time = 10
        tree.tick()
        self.assertEqual(throttle.status, Status.SUCCESS)
        self.assertEqual(test_node.update_count, 2)

        throttle.time = 11
        throttle.policy = 'running'
        tree.tick()
        self.assertEqual(throttle.status, Status.RUNNING)
        self.assertEqual(test_node.update_count, 2)

        throttle.time = 15
        tree.tick()
        self.assertEqual(throttle.status, Status.SUCCESS)
        self.assertEqual(test_node.update_count, 3)


class TestIsStatusChanged(unittest.TestCase):
    def setUp(self):
        logging.level = logging.Level.DEBUG

    class TestNode(Node):
        def update(self) -> Status:
            return self.status

    def test_is_status_changed_1(self):
        test_node = self.TestNode()
        is_status_changed = IsStatusChanged(
                children=[
                    test_node
                ]
        )

        tree = Tree(root=is_status_changed)
        tree.setup()
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        test_node.status = Status.SUCCESS
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.SUCCESS)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        test_node.status = Status.FAILURE
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.SUCCESS)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)

    def test_is_status_changed_2(self):
        test_node = self.TestNode()
        is_status_changed = IsStatusChanged(
                children=[
                    test_node
                ],
                immediate=True
        )
        tree = Tree(root=is_status_changed)
        tree.setup()
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.SUCCESS)
        test_node.status = Status.SUCCESS
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.SUCCESS)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        test_node.status = Status.FAILURE
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.SUCCESS)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)

    def test_is_status_changed_3(self):
        test_node = self.TestNode()
        is_status_changed = IsStatusChanged(
                children=[
                    test_node
                ],
                from_status=[Status.SUCCESS],
                to_status=[Status.FAILURE],
                immediate=True
        )
        tree = Tree(root=is_status_changed)
        tree.setup()
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        test_node.status = Status.SUCCESS
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        test_node.status = Status.FAILURE
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.SUCCESS)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        test_node.status = Status.SUCCESS
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
        tree.tick()
        self.assertEqual(is_status_changed.status, Status.FAILURE)
