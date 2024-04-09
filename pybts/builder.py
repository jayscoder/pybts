from __future__ import annotations

import json
import os.path
from typing import Callable
import xml.etree.ElementTree as ET
import copy
from pybts.node import *
from pybts.composites import *
from pybts.decorators import *
import uuid
from pybts.utility import camel_case_to_snake_case
from pybts.ref_file import RefFile


class Builder:
    def __init__(self, folders: str | list = '', global_attrs: dict = None):
        self.repo = { }  # 注册节点的仓库
        self.repo_desc = { }  # 仓库的描述
        self.register_default()
        self.global_attrs = global_attrs or { }  # 全局参数，会在build时传递给每一个节点
        if isinstance(folders, str):
            self.folders = [folders]
        else:
            self.folders = folders

    def register(self, name: str | list[str], creator: Callable, desc: str = ''):
        if isinstance(name, str):
            name_list = name.split('|')
            for _name in name_list:
                self.repo[_name] = creator
                if desc != '':
                    self.repo_desc[_name] = desc.strip()
        else:
            for _name in name:
                self.register(_name, creator, desc=desc)

    def register_node(self, *nodes: Node.__class__):
        """
        注册节点，注意节点的__init__传递的参数全部都是str类型，在内部要自己处理一下
        """
        for node in nodes:
            self.register(node.__name__, node, desc=node.__doc__ or node.__name__)
            self.register(camel_case_to_snake_case(node.__name__), node)
            module_name = f'{node.__module__}.{node.__name__}'
            self.register(module_name, node)

    def read_text_from_file(self, filepath: str) -> str:
        # 从folder中找文件
        if os.path.exists(filepath) and os.path.isfile(filepath):
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()

        # 遍历文件夹列表里所有的文件，找到和文件名相同的文件并返回内容
        for folder in self.folders:
            folder_filepath = os.path.join(folder, filepath)
            if os.path.exists(folder_filepath) and os.path.isfile(folder_filepath):
                with open(folder_filepath, 'r', encoding='utf-8') as file:
                    return file.read()

        raise Exception(f'Cannot find file: {filepath}')

    def build_from_file(self, filepath: str):
        text = self.read_text_from_file(filepath=filepath)
        if filepath.endswith('.json'):
            return self.build_from_json(json_data=text, ignore_children=False)
        elif filepath.endswith('.xml'):
            return self.build_from_xml(xml_data=text, ignore_children=False)
        else:
            raise Exception('Unsupported file')

    def build_from_xml(self, xml_data: ET.Element | str, ignore_children: bool = False) -> Node:
        if isinstance(xml_data, str):
            xml_data = ET.fromstring(xml_data)
        from pybts.utility import xml_to_json
        return self.build_from_json(
                json_data=xml_to_json(
                        xml_node=xml_data, ignore_children=ignore_children),
                ignore_children=ignore_children)

    def build_from_json(self, json_data: dict | str, ignore_children: bool = False) -> Node:

        if isinstance(json_data, str):
            json_data = json.loads(json_data, encoding='utf-8')
        tag = json_data['tag']
        assert tag in self.repo, f'Unsupported tag {tag}'
        creator = self.repo[tag]
        children = []
        if not ignore_children:
            children = [self.build_from_json(json_data=child, ignore_children=ignore_children) for child in
                        json_data['children']]
        data = copy.copy(json_data['data'])

        # if 'name' not in data:
        #     data['name'] = json_data['tag']

        attrs = {
            **self.global_attrs,
            **data,
        }
        try:
            node = creator(**attrs, children=children)
        except Exception as e:
            print(creator, e)
            raise e
        node.attrs = attrs

        if BT_PRESET_DATA_KEY.ID in data and data[BT_PRESET_DATA_KEY.ID]:
            node.id = uuid.UUID(data[BT_PRESET_DATA_KEY.ID])
        if BT_PRESET_DATA_KEY.STATUS in data and data[BT_PRESET_DATA_KEY.STATUS]:
            node.status = Status(data[BT_PRESET_DATA_KEY.STATUS])

        if isinstance(node, Action) and 'actions' in data and data['actions']:
            for action in data['actions']:
                node.actions.put_nowait(action)
        return node

    def register_default(self):
        self.register_node(
                Sequence,
                SequenceWithMemory,
                ReactiveSequence,
                Parallel,
                ReactiveSelector,
                Selector,
                ReactiveSelector,
                SelectorWithMemory,
                ConditionBranch,
                Template,
                PreCondition,
                PostCondition
        )

        self.register_node(
                Failure,
                Success,
                Running,
        )

        self.register_node(
                Inverter,
                RunningUntilCondition,
                OneShot,
                Count,
                RunningIsFailure,
                RunningIsSuccess,
                FailureIsSuccess,
                FailureIsRunning,
                SuccessIsFailure,
                SuccessIsRunning,
        )

        self.register_node(RefFile)

        # 且或非
        self.register('And', Sequence)
        self.register('Or', Selector)
        self.register('Not', Inverter)
        self.register('Root', Parallel)  # 可以作为根节点
        # 强化学习


if __name__ == '__main__':
    builder = Builder()
    print(builder.repo_desc)
    # print(Node.__doc__)
