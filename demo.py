from __future__ import annotations
from py_trees import common
import pybts

class Person(pybts.Action):
    def __init__(self, age: int | str, **kwargs):
        super().__init__(**kwargs)
        self.age = int(age)
        self.cache = self.attach_blackboard_client()
        self.cache.register_key('age', pybts.Access.WRITE)

    def update(self) -> common.Status:
        self.age += 1
        return common.Status.SUCCESS

    def to_data(self):
        return {
            'age' : self.age,
            'test': {
                'hello': {
                    'world': 1
                }
            }
        }

builder = pybts.builder.Builder()
builder.register_node(Person)
root = builder.build_from_file('demos/demo_bt.xml')
tree = pybts.Tree(root=root, name='Person')

board = pybts.board.Board(tree=tree, log_dir='logs')

if __name__ == '__main__':
    for node in tree.root.iterate():
        print(node.__str__())

    # pybts.logging.level = pybts.logging.Level.DEBUG
    # for data in board.iterate():
    #     print(data)
    #     break
    # board.clear()
    # for i in range(10000):
    #     tree.tick()
    #     board.track(info={
    #         'test_info': i,
    #     })
    #     time.sleep(0.5)
    #     if i % 5 == 0:
    #         tree.reset()
    #     print(i)
    # WebUI
    # python -m pybts.board_server --dir=logs --debug --host=localhost --port=10000
    # or pybts - -dir = logs - -debug - -host = localhost - -port = 10000
