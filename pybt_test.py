import time
from py_trees import common
import pybt

class Person(pybt.Action):
    def __init__(self, name: str, age: int):
        super().__init__(name=name)
        self.age = age

    @classmethod
    def creator(cls, d, c):
        return Person(name=d['name'], age=int(d['age']))

    def update(self) -> common.Status:
        self.age += 1
        return common.Status.SUCCESS

    def to_data(self):
        return {
            'age': self.age
        }


builder = pybt.builder.Builder()
builder.register('Person', Person.creator)
root = builder.build_from_file('demos/demo_bt.xml')
tree = pybt.Tree(root=root, name='Person')

bt_board = pybt.board.Board(tree=tree, log_dir='logs')

if __name__ == '__main__':
    bt_board.clear()
    for i in range(10000):
        tree.tick()
        bt_board.track(info={
            'test_info': i
        })
        time.sleep(0.5)
        print(i)
