import os
import typing

from pybts import utility
from pybts.tree import Tree
import jsonpickle


class Board:
    def __init__(self, tree: Tree, log_dir: str = '.'):
        self.tree = tree
        self.log_dir = os.path.join(log_dir, tree.name)
        self.history_dir = os.path.join(self.log_dir, 'pybts-history')
        self.current_path = os.path.join(self.log_dir, 'pybts.json')
        os.makedirs(self.history_dir, exist_ok=True)
        self.track_id = 0

    def track(self, info: dict = None):
        """
        track当前运行信息
        :param info: 额外信息
        :return:
        """
        self.track_id += 1
        json_data = {
            'id'   : self.track_id,
            'step' : self.tree.count,
            'round': self.tree.round,
            'stage': f'{self.tree.round}-{self.tree.count}',
            'info' : info,
            'tree' : utility.bt_to_json(self.tree.root),
        }

        json_text = jsonpickle.dumps(json_data, indent=4)
        history_path = os.path.join(self.history_dir, f'{self.track_id}.json')
        with open(history_path, 'w') as f:
            f.write(json_text)
        with open(self.current_path, 'w') as f:
            f.write(json_text)

    def clear(self):
        self.track_id = 0
        if os.path.exists(self.history_dir):
            utility.delete_folder_contents(self.history_dir)
        if os.path.exists(self.current_path):
            os.remove(self.current_path)

    def iterate(self) -> typing.Iterator[dict]:
        # 遍历所有的历史数据
        # if os.path.exists(self.current_path):
        #     with open(self.current_path, 'r', encoding='utf') as f:
        #         json_data = jsonpickle.loads(f.read())
        #         yield json_data
        if os.path.exists(self.history_dir):
            for filename in os.listdir(self.history_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.history_dir, filename)
                    with open(filepath, 'r', encoding='utf') as f:
                        json_data = jsonpickle.loads(f.read())
                        yield json_data


