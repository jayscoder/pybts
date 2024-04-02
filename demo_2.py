import logging
import time
import typing

import py_trees
from py_trees import common
from py_trees.common import Status

import pybts


class ToggleStatus(pybts.Condition):
    def __init__(self, status_list: list, name: str = ''):
        super().__init__(name=name)
        self.init_count = 0
        self.update_count = 0
        self.terminate_count = 0
        self.status_list = status_list

    def updater(self) -> typing.Iterator[Status]:
        self.update_count = 0
        while True:
            yield self.status_list[self.update_count]
            self.update_count = (self.update_count + 1) % len(self.status_list)

    def to_data(self):
        return {
            'init_count'     : self.init_count,
            'update_count'   : self.update_count,
            'terminate_count': self.terminate_count,
            'status_list'    : self.status_list
        }

    def terminate(self, new_status: common.Status) -> None:
        self.terminate_count += 1

    def initialise(self) -> None:
        self.init_count += 1


class Success(pybts.Success):
    def __init__(self, name: str = ''):
        super().__init__(name=name)
        self.update_count = 0
        self.stop_count = 0

    def update(self) -> Status:
        self.update_count += 1
        return super().update()

    def to_data(self):
        return {
            'update_count': self.update_count,
            'stop_count'  : self.stop_count,
        }

    def stop(self, new_status: common.Status) -> None:
        super().stop(new_status)
        self.stop_count += 1


class Failure(pybts.Failure):
    def __init__(self, name: str = ''):
        super().__init__(name=name)
        self.update_count = 0
        self.stop_count = 0

    def update(self) -> Status:
        self.update_count += 1
        return super().update()

    def to_data(self):
        return {
            'update_count': self.update_count,
            'stop_count'  : self.stop_count,
        }

    def stop(self, new_status: common.Status) -> None:
        super().stop(new_status)
        self.stop_count += 1


class Running(pybts.Running):
    def __init__(self, name: str = ''):
        super().__init__(name=name)
        self.update_count = 0
        self.stop_count = 0

    def update(self) -> Status:
        self.update_count += 1
        return super().update()

    def to_data(self):
        return {
            'update_count': self.update_count,
            'stop_count'  : self.stop_count,
        }

    def stop(self, new_status: common.Status) -> None:
        super().stop(new_status)
        self.stop_count += 1


_name_index = -1


def new_name():
    global _name_index
    _name_index += 1
    return str(_name_index)


if __name__ == '__main__':
    pybts.logging.level = pybts.logging.Level.DEBUG

    status_list_1 = [Status.SUCCESS, Status.RUNNING, Status.RUNNING, Status.FAILURE]
    node = pybts.Selector(
            children=[
                pybts.Parallel(
                        children=[
                            ToggleStatus(name=new_name(), status_list=status_list_1),
                            ToggleStatus(name=new_name(), status_list=status_list_1),
                            ToggleStatus(name=new_name(), status_list=status_list_1),
                        ],
                ),
                pybts.Parallel(
                        children=[
                            ToggleStatus(name=new_name(), status_list=status_list_1),
                            ToggleStatus(name=new_name(), status_list=status_list_1),
                            ToggleStatus(name=new_name(), status_list=status_list_1),
                        ],
                )
            ]
    )

    tree = pybts.Tree(node, name='DEMO_Sequence')
    tree.setup()
    board = pybts.Board(tree=tree, log_dir='./logs')
    board.clear()

    for r in range(10):
        tree.reset()
        for i in range(10):
            tree.tick()
            board.track()
            time.sleep(0.5)

    print(tree.tip().name)
