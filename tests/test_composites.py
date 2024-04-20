import logging
import unittest
from pybts import *


class ToggleStatus(Node, Condition):

    def __init__(self, status_list: list[Status], **kwargs):
        super().__init__(**kwargs)
        self.status_list = status_list
        self.curr_index = -1

    def update(self) -> Status:
        self.curr_index = (self.curr_index + 1) % len(self.status_list)
        return self.status_list[self.curr_index]


class TestCondBranch(unittest.TestCase):

    def test_cond_branch(self):
        root = CondBranch(children=[
            Success(),
            Print(msg='1'),
            Print(msg='2')
        ])
        tree = Tree(root=root).setup()
        tree.tick()

        self.assertEqual(root.status, Status.SUCCESS)
        self.assertEqual(root.current_index, 1)

        root = CondBranch(children=[
            Failure(),
            Print(msg='1'),
            Print(msg='2')
        ])
        tree = Tree(root=root).setup()
        tree.tick()

        self.assertEqual(root.status, Status.SUCCESS)
        self.assertEqual(root.current_index, 2)

        root = CondBranch(children=[
            Running(),
            Print(msg='1'),
            Print(msg='2')
        ])
        tree = Tree(root=root).setup()
        tree.tick()

        self.assertEqual(root.status, Status.RUNNING)
        self.assertEqual(root.current_index, 0)

    def test_cond_branch2(self):
        root = CondBranch(children=[
            ToggleStatus(status_list=[Status.SUCCESS, Status.FAILURE, Status.RUNNING, Status.RUNNING, Status.SUCCESS,
                                      Status.FAILURE]),
            Print(msg='1'),
            Print(msg='2')
        ])
        tree = Tree(root=root).setup()
        tree.tick()

        self.assertEqual(root.status, Status.SUCCESS)
        self.assertEqual(root.current_index, 1)

        tree.tick()

        self.assertEqual(root.status, Status.SUCCESS)
        self.assertEqual(root.current_index, 2)

        tree.tick()

        self.assertEqual(root.status, Status.RUNNING)
        self.assertEqual(root.current_index, 0)

        tree.tick()

        self.assertEqual(root.status, Status.RUNNING)
        self.assertEqual(root.current_index, 0)

        tree.tick()

        self.assertEqual(root.status, Status.SUCCESS)
        self.assertEqual(root.current_index, 1)

        tree.tick()

        self.assertEqual(root.status, Status.SUCCESS)
        self.assertEqual(root.current_index, 2)
