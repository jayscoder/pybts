import logging
import unittest
from pybts import *


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



