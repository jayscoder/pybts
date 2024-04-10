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

    def get_relative_filename(self, filepath: str):
        """获取文件的相对文件名，相对于目前注册的folder"""
        if os.path.exists(filepath):
            # 如果路径存在的话，说明本身不是相对路径
            for folder in self.folders:
                rl_path = os.path.relpath(filepath, folder)
                if not rl_path.startswith('..'):
                    return os.path.splitext(rl_path)[0]

        # 路径不存在，说明已经是注册在folder底下的相对路径，直接返回即可
        return os.path.splitext(filepath)[0]

    def find_filepath(self, filepath: str):
        """
        从builder注册的folder找到需要打开的完整路径
        """
        if os.path.exists(filepath) and os.path.isfile(filepath):
            return filepath

        # 遍历文件夹列表里所有的文件，找到和文件名相同的文件并返回内容
        for folder in self.folders:
            folder_filepath = os.path.join(folder, filepath)
            if os.path.exists(folder_filepath) and os.path.isfile(folder_filepath):
                return folder_filepath

        return ''

    def read_text_from_file(self, filepath: str) -> str:
        # 从folder中找文件
        filepath = self.find_filepath(filepath=filepath)
        if filepath != '' and os.path.exists(filepath) and os.path.isfile(filepath):
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()

        raise Exception(f'Cannot find file: {filepath}')

    def build_from_file(self, filepath: str, attrs: dict = None):
        """
        attrs: 传递给每个节点的参数，优先级弱于节点本身设置的参数，高于builder设置的global_attrs参数
        """
        text = self.read_text_from_file(filepath=filepath)
        if filepath.endswith('.json'):
            return self.build_from_json(json_data=text, ignore_children=False, attrs=attrs)
        elif filepath.endswith('.xml'):
            return self.build_from_xml(xml_data=text, ignore_children=False, attrs=attrs)
        else:
            raise Exception('Unsupported file')

    def build_from_xml(self, xml_data: ET.Element | str, ignore_children: bool = False, attrs: dict = None) -> Node:
        if isinstance(xml_data, str):
            xml_data = ET.fromstring(xml_data)
        from pybts.utility import xml_to_json
        return self.build_from_json(
                json_data=xml_to_json(
                        xml_node=xml_data, ignore_children=ignore_children),
                ignore_children=ignore_children,
                attrs=attrs
        )

    def build_from_json(self, json_data: dict | str, ignore_children: bool = False, attrs: dict = None) -> Node:
        if isinstance(json_data, str):
            json_data = json.loads(json_data, encoding='utf-8')
        tag = json_data['tag']
        data = copy.copy(json_data['data'])

        # 实现include逻辑，可以在这里引用别的节点
        if tag.lower() == 'include':
            filepath = data['path']
            del data['path']
            # include节点设置的参数可以传递给构建的每个节点
            return self.build_from_file(filepath=filepath, attrs=data)

        assert tag in self.repo, f'Unsupported tag {tag}'
        creator = self.repo[tag]
        children = []
        if not ignore_children:
            children = [self.build_from_json(
                    json_data=child,
                    ignore_children=ignore_children) for child in
                json_data['children']]

        try:
            node_attrs = {
                **self.global_attrs,
                **(attrs or { }),
                **data,
            }
            node = creator(**node_attrs, children=children, builder=self)
            node.attrs = node_attrs
        except Exception as e:
            print(creator, e)
            raise e

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
                PostCondition,
                Print
        )

        self.register_node(
                Failure,
                Success,
                Running,
                IsChanged,
                IsMatchRule
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
                Timeout,
                Throttle,
        )

        # 且或非
        self.register('And', Sequence)
        self.register('Or', Selector)
        self.register('Not', Inverter)
        self.register('Root', Parallel)  # 可以作为根节点
        # 强化学习

    def to_dict(self):
        return {
            'folders': self.folders,
            'nodes'  : len(self.repo_desc)
        }

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4, ensure_ascii=False)

    def __repr__(self):
        return self.__str__()


if __name__ == '__main__':
    builder = Builder()
    print(builder.repo_desc)
    # print(Node.__doc__)
    # rel_path = os.path.relpath('c', 'b')
    # print(rel_path)
