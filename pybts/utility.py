from __future__ import annotations

import py_trees.blackboard

from pybts.node import *
from pybts.constants import *
import yaml
from queue import Queue
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import json
import jinja2


def read_queue_without_destroying(q: Queue):
    # 创建一个空列表来存储队列中的元素
    temp_list = []

    # 遍历队列，复制元素到列表和临时队列
    while not q.empty():
        item = q.get_nowait()
        temp_list.append(item)

    # 将元素重新放入原始队列，保持原始状态不变
    for item in temp_list:
        q.put_nowait(item)

    return temp_list


def bt_to_node_type(node: py_trees.behaviour.Behaviour) -> str:
    if isinstance(node, py_trees.composites.Composite):
        return BT_NODE_TYPE.COMPOSITE
    elif isinstance(node, py_trees.decorators.Decorator):
        return BT_NODE_TYPE.DECORATOR
    elif isinstance(node, Condition):
        return BT_NODE_TYPE.CONDITION
    else:
        return BT_NODE_TYPE.ACTION


def bt_to_json(node: py_trees.behaviour.Behaviour, ignore_children: bool = False) -> dict:
    info = {
        'tag'     : node.__class__.__name__,
        'children': [],
        'data'    : {
            BT_PRESET_DATA_KEY.ID               : node.id.hex,
            BT_PRESET_DATA_KEY.STATUS           : node.status.name,
            BT_PRESET_DATA_KEY.TYPE             : bt_to_node_type(node),
            BT_PRESET_DATA_KEY.TAG              : node.__class__.__name__,
            BT_PRESET_DATA_KEY.FEEDBACK_MESSAGES: node.feedback_message,
            BT_PRESET_DATA_KEY.NAME             : node.name,
            BT_PRESET_DATA_KEY.CHILDREN_COUNT   : len(node.children)
        },
    }

    if isinstance(node, Node):
        info['data'] = {
            **info['data'],
            **node.to_data(),
        }

    if not ignore_children:
        info['children'] = [bt_to_json(child, ignore_children=ignore_children) for child in node.children]
    return info


def bt_to_echarts_json(node: dict | py_trees.behaviour.Behaviour | ET.Element, ignore_children: bool = False) -> dict:
    if isinstance(node, py_trees.behaviour.Behaviour):
        node = bt_to_json(node, ignore_children=ignore_children)
    if isinstance(node, ET.Element):
        node = xml_to_json(node, ignore_children=ignore_children)

    symbol = BT_NODE_TYPE_TO_ECHARTS_SYMBOLS[node['data'][BT_PRESET_DATA_KEY.TYPE]]
    symbolSize = BT_NODE_TYPE_TO_ECHARTS_SYMBOL_SIZE[node['data'][BT_PRESET_DATA_KEY.TYPE]]
    tooltip = yaml.dump(node['data'], allow_unicode=True, indent=4)

    d = {
        'name'      : node['data'][BT_PRESET_DATA_KEY.ID],
        'value'     : tooltip,
        'label'     : node['data']['name'],
        'data'      : node,
        'itemStyle' : {
            'color'      : STATUS_TO_ECHARTS_SYMBOL_COLORS[node['data'][BT_PRESET_DATA_KEY.STATUS]],
            'borderColor': STATUS_TO_ECHARTS_SYMBOL_COLORS[node['data'][BT_PRESET_DATA_KEY.STATUS]],
        },
        'symbolSize': symbolSize,
        'symbol'    : symbol,
        'children'  : [],
        'lineStyle' : {
            # 'type' : STATUS_TO_ECHARTS_LINE_STYLE_TYPE[node['data'][BT_PRESET_DATA_KEY.STATUS]],
            'color': STATUS_TO_ECHARTS_LINE_STYLE_COLOR[node['data'][BT_PRESET_DATA_KEY.STATUS]],
        },
    }

    if not ignore_children:
        d['children'] = [bt_to_echarts_json(child, ignore_children) for child in node['children']]
    return d


def bt_to_xml_node(node: dict | py_trees.behaviour.Behaviour, ignore_children=False) -> ET.Element:
    if isinstance(node, py_trees.behaviour.Behaviour):
        node = bt_to_json(node, ignore_children=ignore_children)
    attribs = { key: str(value) for key, value in node['data'].items() }
    xml_node = ET.Element(node['tag'], attrib=attribs)
    if not ignore_children:
        for child in node['children']:
            xml_node.append(bt_to_xml_node(child, ignore_children=ignore_children))
    return xml_node


def xml_node_to_string(xml_node: ET.Element) -> str:
    text = ET.tostring(xml_node, encoding='utf-8').decode('utf-8')
    text = minidom.parseString(text).toprettyxml(indent='    ').replace('<?xml version="1.0" ?>', '').strip()
    return text


def bt_to_xml(node: dict | py_trees.behaviour.Behaviour, ignore_children=False) -> str:
    xml_node = bt_to_xml_node(node, ignore_children=ignore_children)
    return xml_node_to_string(xml_node)


def xml_to_json(xml_node: ET.Element | str, ignore_children=False) -> dict:
    if isinstance(xml_node, str):
        xml_node = ET.fromstring(xml_node)

    attrib = xml_node.attrib
    json_data = {
        'tag'           : xml_node.tag,
        'data'          : attrib,
        'children_count': len(xml_node),
        'children'      : []
    }
    if not ignore_children:
        json_data['children'] = [xml_to_json(child) for child in xml_node]
    return json_data


def delete_folder_contents(folder_path):
    # 列出文件夹中的所有文件和子文件夹
    for item in os.listdir(folder_path):
        # 构建文件或子文件夹的完整路径
        item_path = os.path.join(folder_path, item)
        # 如果是文件，则删除
        if os.path.isfile(item_path):
            os.remove(item_path)
        # 如果是子文件夹，则递归调用该函数删除其内容
        elif os.path.isdir(item_path):
            delete_folder_contents(item_path)
            # 删除空文件夹
            os.rmdir(item_path)


def blackboards_to_json(*blackboards: py_trees.blackboard.Client) -> dict:
    json_data = { }
    for b in blackboards:
        keys = b.remappings.values()
        for k in keys:
            json_data[k] = py_trees.blackboard.Blackboard.storage.get(k, None)
    return json_data


class PYBTJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        import datetime
        import enum
        import uuid

        try:
            return super().default(obj)
        except TypeError:
            pass

        if isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, enum.Enum):
            return obj.value
        elif isinstance(obj, tuple):
            return list(obj)  # Convert tuple to list
        elif isinstance(obj, uuid.UUID):
            return obj.hex  # Convert UUID to string
        elif isinstance(obj, set):
            return list(set)
        elif isinstance(obj, Status):
            return obj.value
        else:
            try:
                import numpy as np
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, np.bool_):
                    return bool(obj)
                elif isinstance(obj, np.str_):
                    return str(obj)
                elif isinstance(obj, enum.Enum):
                    return obj.value
                elif isinstance(obj, tuple):
                    return list(obj)  # Convert tuple to list
                elif isinstance(obj, np.unicode_):
                    return str(obj)
            except:
                pass
            return str(obj)


def json_dumps(json_data, indent=4, sort_keys=False, ensure_ascii=True, **kwargs):
    return json.dumps(json_data, cls=PYBTJsonEncoder, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii,
                      **kwargs)


def json_dump(json_data, fp, indent=4, sort_keys=False, ensure_ascii=True, **kwargs):
    return json.dump(json_data, fp, cls=PYBTJsonEncoder, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii,
                     **kwargs)


def json_loads(s, **kwargs):
    return json.loads(s, **kwargs)


# def clear_blackboards(*blackboards: py_trees.blackboard.Client):
#     for b in blackboards:
#         keys = b.remappings.values()
#         for k in keys:
#             b.unset(k)

def extract_project_path_list(log_dir: str) -> [str]:
    """提取出项目列表"""
    projects = []
    for dirpath, dirnames, filenames in os.walk(log_dir):
        if 'pybts.json' in filenames:
            relative_path = os.path.relpath(dirpath, log_dir)
            projects.append(relative_path)
    return projects


def clear_project(log_dir: str, project: str):
    current_path = os.path.join(log_dir, project, 'pybts.json')
    if os.path.exists(current_path):
        os.remove(current_path)
    history_dir = os.path.join(log_dir, project, 'history')
    if os.path.exists(history_dir):
        delete_folder_contents(history_dir)


def jinja2_render(template: str, context: dict) -> str:
    return jinja2.Template(template).render(context)
