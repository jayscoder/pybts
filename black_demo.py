from py_trees.common import Status
import py_trees
import pybts
from cachetools import Cache


class TestNodeA(pybts.Action):

    def __init__(self):
        super().__init__()
        self.cache = self.attach_blackboard_client(name='cache', namespace='a')
        self.cache.register_key('value', pybts.Access.WRITE)
        self.cache.register_key('age', pybts.Access.WRITE)
        self.cache.register_key('name', pybts.Access.WRITE)
        # self.cache.name = '1'
        # self.cache.age = 'a'
        # self.cache.value = 1

    def update(self) -> Status:
        self.cache.value = 1
        return Status.SUCCESS


class TestNodeB(pybts.Action):

    def __init__(self):
        super().__init__()
        self.cache = self.attach_blackboard_client(name='cache', namespace='a')
        self.cache.register_key('value', pybts.Access.WRITE)
        self.cache.register_key('age', pybts.Access.WRITE)
        self.cache.register_key('name', pybts.Access.WRITE)

    def update(self) -> Status:
        print(py_trees.blackboard.Blackboard.storage)
        return Status.FAILURE


if __name__ == '__main__':

    node = pybts.Parallel(
            name='',
            children=[
                # TestNodeA(),
                TestNodeA(),
                # TestNodeA(),
                TestNodeB()
            ],
            success_threshold=-1
    )
    node.setup()
    node.tick_once()
    print(node.status)
