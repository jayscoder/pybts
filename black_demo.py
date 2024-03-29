from py_trees.common import Status
import py_trees
import pybts
from cachetools import Cache


class TestNode(pybts.Action):

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


class TestNode2(pybts.Action):

    def __init__(self, name: str):
        super().__init__(name=name)
        self.cache = self.attach_blackboard_client(name='cache', namespace='a')
        self.cache.register_key('value', pybts.Access.WRITE)
        self.cache.register_key('age', pybts.Access.WRITE)
        self.cache.register_key('name', pybts.Access.WRITE)

    def update(self) -> Status:
        print(py_trees.blackboard.Blackboard.storage)
        return Status.SUCCESS


if __name__ == '__main__':
    seq = pybts.Sequence(
            name='',
            children=[
                TestNode(),
                TestNode2('test2')
            ])
    # print(pybts.utility.bt_blackboards_to_json(seq.children[0]))
    # seq.tick_once()
    print(seq.children[0].name)
