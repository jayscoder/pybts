import os
from pybts import utility
from pybts.tree import Tree
import jsonpickle as json
class Board:
    def __init__(self, tree: Tree, log_dir: str = '.'):
        self.tree = tree
        self.log_dir = os.path.join(log_dir, tree.name)
        self.history_dir = os.path.join(self.log_dir, 'pybts-history')
        self.current_path = os.path.join(self.log_dir, 'pybts.json')
        os.makedirs(self.history_dir, exist_ok=True)

    def track(self, info: dict = None):
        """
        track当前运行信息
        :param info: 额外信息
        :return:
        """
        json_data = {
            'step' : self.tree.count,
            'round': self.tree.round,
            'stage': f'{self.tree.round}-{self.tree.count}',
            'tree' : utility.bt_to_json(self.tree.root),
            'info' : info
        }

        json_text = json.dumps(json_data, indent=4)
        history_path = os.path.join(self.history_dir, f'{self.tree.round}-{self.tree.count}.json')
        with open(history_path, 'w') as f:
            f.write(json_text)
        with open(self.current_path, 'w') as f:
            f.write(json_text)

    def clear(self):
        if os.path.exists(self.history_dir):
            utility.delete_folder_contents(self.history_dir)
        if os.path.exists(self.current_path):
            os.remove(self.current_path)
