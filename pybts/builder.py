from __future__ import annotations

import json
from typing import Callable
import xml.etree.ElementTree as ET
import copy
from pybts.constants import *
from pybts.node import *
from pybts.composites import *
from pybts.decorators import *
import uuid


class Builder:
    def __init__(self):
        self.repo = { }
        self.repo_desc = { }  # 仓库的描述
        self.repo_node = { }  # 注册的bt节点
        self.register_default()

    def register(self, name: str | list[str], creator: Callable[[dict, [Node]], Node], desc: str = ''):
        if isinstance(name, str):
            name_list = name.split('|')
            for _name in name_list:
                self.repo[_name] = creator
                if desc != '':
                    self.repo_desc[_name] = desc.strip()
        else:
            for _name in name:
                self.register(_name, creator, desc=desc)

    def register_bt(self, *nodes: Node.__class__):
        for node in nodes:
            self.repo_node[node.__name__] = node
            self.register(node.__name__, node.creator, desc=node.__doc__ or node.__name__)
            module_name = f'{node.__module__}.{node.__name__}'
            self.register(module_name, node.creator)

    def build_from_file(self, filepath: str):
        with open(filepath, 'r') as f:
            text = f.read()
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
        return self.build_from_json(json_data=xml_to_json(xml_node=xml_data, ignore_children=ignore_children),
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
        if 'name' not in data:
            data['name'] = json_data['tag']
        node = creator(data, children)
        if BT_PRESET_DATA_KEY.ID in data and data[BT_PRESET_DATA_KEY.ID]:
            node.id = uuid.UUID(data[BT_PRESET_DATA_KEY.ID])
        if BT_PRESET_DATA_KEY.STATUS in data and data[BT_PRESET_DATA_KEY.STATUS]:
            node.status = Status(data[BT_PRESET_DATA_KEY.STATUS])

        if isinstance(node, Action) and 'actions' in data and data['actions']:
            for action in data['actions']:
                node.actions.put_nowait(action)
        return node

    def register_default(self):
        self.register_bt(
                Sequence,
                SequenceWithMemory,
                ReactiveSequence,
                Parallel,
                ReactiveSelector,
                Selector,
                ReactiveSelector,
                SelectorWithMemory,
                ConditionBranch,
        )

        self.register_bt(
                Failure,
                Success,
                Running
        )

        self.register_bt(
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


if __name__ == '__main__':
    builder = Builder()
    print(builder.repo_desc)
    # print(Node.__doc__)
