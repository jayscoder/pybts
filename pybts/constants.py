from py_trees.common import Status, Access
from enum import Enum


def _hex_color(color: str) -> tuple[int, int, int]:
    # 将十六进制颜色代码转换为RGB值
    r = int(color[0:2], 16)  # 转换红色分量
    g = int(color[2:4], 16)  # 转换绿色分量
    b = int(color[4:6], 16)  # 转换蓝色分量
    return r, g, b


def _echarts_color(color: str) -> str:
    r, g, b = _hex_color(color)
    return f'rgb({r},{g},{b})'


# Map of color names to RGB values
ECHARTS_COLORS = {
    # "red"   : _echarts_color('d81e06'),
    "red"       : _echarts_color('F95D7B'),
    # "blue"  : _echarts_color('1296db'), # 0AD2F3
    'blue'      : _echarts_color('0AD2F3'),
    # "green" : _echarts_color('1afa29'),
    'green'     : _echarts_color('3BBD73'),
    "pink"      : _echarts_color('d4237a'),
    'purple'    : _echarts_color('AB69E9'),
    # "yellow": _echarts_color('f4ea2a'),
    'yellow'    : _echarts_color('FED969'),
    # "grey"  : _echarts_color('8a8a8a'),
    'grey'      : _echarts_color('888888'),
    'light_grey': _echarts_color('bbbbbb'),
    'black'     : _echarts_color('555555'),
    'white'     : _echarts_color('ffffff')
}

STATUS_TO_ECHARTS_SYMBOL_COLORS = {
    Status.SUCCESS.name: ECHARTS_COLORS['blue'],
    Status.FAILURE.name: ECHARTS_COLORS['red'],
    Status.RUNNING.name: ECHARTS_COLORS['yellow'],
    Status.INVALID.name: ECHARTS_COLORS['grey'],
}

STATUS_TO_ECHARTS_LINE_STYLE_COLOR = {
    Status.SUCCESS.name: ECHARTS_COLORS['light_grey'],
    Status.FAILURE.name: ECHARTS_COLORS['light_grey'],
    Status.RUNNING.name: ECHARTS_COLORS['light_grey'],
    Status.INVALID.name: ECHARTS_COLORS['light_grey'],
}


class ECHARTS_SYMBOLS:
    CIRCLE = 'circle'
    RECT = 'rect'
    ROUNDRECT = 'roundRect'
    TRIANGLE = 'triangle'
    DIAMOND = 'diamond'
    PIN = 'pin'
    ARROW = 'arrow'
    NONE = 'none'


class BT_NODE_TYPE:
    # 行为树节点的类型
    COMPOSITE = 'composite'
    DECORATOR = 'decorator'
    ACTION = 'action'
    CONDITION = 'condition'


BT_NODE_TYPE_TO_ECHARTS_SYMBOLS = {
    BT_NODE_TYPE.COMPOSITE: ECHARTS_SYMBOLS.ROUNDRECT,
    BT_NODE_TYPE.DECORATOR: ECHARTS_SYMBOLS.CIRCLE,
    BT_NODE_TYPE.ACTION   : ECHARTS_SYMBOLS.RECT,
    BT_NODE_TYPE.CONDITION: ECHARTS_SYMBOLS.DIAMOND
}

BT_NODE_TYPE_TO_ECHARTS_SYMBOL_SIZE = {
    BT_NODE_TYPE.COMPOSITE: 24,
    BT_NODE_TYPE.DECORATOR: 15,
    BT_NODE_TYPE.ACTION   : 24,
    BT_NODE_TYPE.CONDITION: 24
}


class ECHARTS_LINE_STYLE_TYPE:
    """枚举类，用于定义 ECharts 中线条的样式类型"""
    SOLID = 'solid'  # 实线
    DASHED = 'dashed'  # 虚线
    DOTTED = 'dotted'  # 点线
    DOUBLE = 'double'  # 双线
    CURVE = 'curve'  # 曲线
    BROKEN = 'broken'  # 折线


STATUS_TO_ECHARTS_LINE_STYLE_TYPE = {
    Status.SUCCESS.name: ECHARTS_LINE_STYLE_TYPE.SOLID,
    Status.FAILURE.name: ECHARTS_LINE_STYLE_TYPE.SOLID,
    Status.RUNNING.name: ECHARTS_LINE_STYLE_TYPE.SOLID,
    Status.INVALID.name: ECHARTS_LINE_STYLE_TYPE.SOLID,
}


class BT_PRESET_DATA_KEY:
    """
    预设键
    """
    ID = 'id'
    TYPE = 'type'
    STATUS = 'status'
    TAG = 'tag'
    BLACKBOARD = 'blackboard'
    FEEDBACK_MESSAGES = 'feedback_message'
    NAME = 'name'
    CHILDREN_COUNT = 'children_count'
