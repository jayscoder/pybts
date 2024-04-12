import logging
import unittest
from pybts import *


class TestIsChanged(unittest.TestCase):

    def test_is_changed_immediate_true(self):
        # 测试 immediate=True 的情况
        logging.level = logging.Level.DEBUG

        is_changed = IsChanged(value='{{value}}', immediate=True)
        tree = Tree(root=is_changed).setup()
        tree.context['value'] = 10

        tree.tick()
        self.assertEqual(Status.SUCCESS, is_changed.status)  # 由于 immediate=True，期望状态为 SUCCESS
        tree.context['value'] = 10
        tree.tick()
        self.assertEqual(Status.FAILURE, is_changed.status)

        tree.context['value'] = 11
        tree.tick()
        self.assertEqual(Status.SUCCESS, is_changed.status)

        tree.tick()
        self.assertEqual(Status.FAILURE, is_changed.status)

        tree.reset()
        tree.tick()
        self.assertEqual(Status.SUCCESS, is_changed.status)  # 由于 immediate=True，期望状态为 SUCCESS
        tree.context['value'] = 0
        tree.tick()
        self.assertEqual(Status.SUCCESS, is_changed.status)

    def test_is_changed_different_values(self):
        # 测试不同的 value 值下的行为
        values = [10, 'abc', True, False, { 'key': 'value' }]
        for value in values:
            is_changed = IsChanged(value=value, immediate=False)
            tree = Tree(root=is_changed).setup()
            tree.context['value'] = value
            tree.tick()
            self.assertEqual(Status.FAILURE, is_changed.status)  # 不同的 value 值应该都导致 FAILURE

    def test_is_changed_no_context_value(self):
        # 测试没有 value 键的情况
        is_changed = IsChanged(value='{{value}}', immediate=False)
        tree = Tree(root=is_changed).setup()
        tree.tick()
        self.assertEqual(Status.FAILURE, is_changed.status)  # 没有设置 value 键应该导致 FAILURE

    def test_is_changed_different_tree_structures(self):
        # 测试不同的树结构中使用 IsChanged 节点的情况
        is_changed = IsChanged(value='{{value}}', immediate=False)
        tree1 = Tree(root=is_changed).setup()
        tree2 = Tree(root=is_changed).setup()
        tree3 = Tree(root=is_changed).setup()
        tree1.context['value'] = 10
        tree2.context['value'] = 'abc'
        tree3.context['value'] = True
        tree1.tick()
        tree2.tick()
        tree3.tick()
        self.assertEqual(Status.FAILURE, is_changed.status)  # 不同的树结构下都应该导致 FAILURE


class TestRandomIntValue(unittest.TestCase):

    def test_random_value(self):
        tree = Tree(root=Sequence(
                children=[
                    RandomIntValue(key='random_int', high=10),
                    Print(msg='{{random_int}}')
                ]
        ))
        tree.setup()
        tree.tick()
        tree.reset()
        print(tree.context)


class TestUpdater(unittest.TestCase):

    def test_updater(self):
        class TestNode(Node):
            def updater(self) -> typing.Iterator[Status]:
                yield Status.SUCCESS
                yield Status.FAILURE

        node1 = TestNode(name='N1')
        node2 = TestNode(name='N2')
        tree = Tree(root=Parallel(
                children=[
                    node1,
                    node2
                ]
        )).setup()
        tree.tick()
        self.assertEqual(Status.SUCCESS, node1.status)
        self.assertEqual(Status.SUCCESS, node2.status)

        tree.tick()
        self.assertEqual(Status.FAILURE, node1.status)
        self.assertEqual(Status.FAILURE, node2.status)

        tree.tick()
        self.assertEqual(Status.SUCCESS, node1.status)
        self.assertEqual(Status.SUCCESS, node2.status)

        tree.tick()
        self.assertEqual(Status.FAILURE, node1.status)
        self.assertEqual(Status.FAILURE, node2.status)
