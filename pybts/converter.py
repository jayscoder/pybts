import typing
import jinja2
import json
from py_trees.common import Status
from typing import Union
import math
import random

_STATUS_MAP = {
    'SUCCESS': Status.SUCCESS,
    'FAILURE': Status.FAILURE,
    'RUNNING': Status.RUNNING,
    'INVALID': Status.INVALID
}


class Converter:

    def __init__(self, node):
        self.node = node

    def parse(self, value: typing.Any, type: str):
        if type == "float":
            return self.float(value)
        elif type == "int":
            return self.int(value)
        elif type == "bool":
            return self.bool(value)
        elif type == "str":
            return self.render(value)
        elif type == 'dict':
            return self.dict(value)
        elif type == 'list':
            return self.list(value)
        elif type == '':
            return self.render(value)
        else:
            raise Exception(f'Converter.parse: Unknown type={type} for value={value}')

    def bool(self, value: typing.Any):
        if isinstance(value, str):
            if value.lower() == 'true':
                return True
            elif value.lower() == 'false':
                return False
            return bool(self.eval(self.render(value)))
        return bool(value)

    def float(self, value: typing.Any):
        if isinstance(value, str):
            return float(self.eval(self.render(value)))
        else:
            return float(value)

    def int(self, value: typing.Any):
        if isinstance(value, str):
            return int(self.eval(self.render(value)))
        else:
            return int(value)

    def eval(self, value: str):
        return eval(value, self.node.context,
                    { 'math': math, 'random': random, 'name': self.node.name })

    @classmethod
    def status(cls, value: Union[str, Status]) -> Status:
        if isinstance(value, Status):
            return value
        value = value.upper()
        if value not in _STATUS_MAP:
            raise Exception(f'{value} is not a valid status')
        return _STATUS_MAP[value]

    @classmethod
    def status_list(cls, value: Union[str, Status, list[Status]], sep: str = ',') -> list[Status]:
        if isinstance(value, Status):
            return [value]
        elif isinstance(value, list):
            return [cls.status(value=item) for item in value]
        elif isinstance(value, str):
            value_list = value.split(sep)
            return [cls.status(value=item) for item in value_list if item != '']

    def int_list(self, value: Union[str, list[int], int], sep: str = ',') -> list[int]:
        if isinstance(value, int):
            return [value]
        elif isinstance(value, list):
            return [self.int(value=item) for item in value]
        elif isinstance(value, str):
            value_list = value.split(sep)
            return [self.int(value=item) for item in value_list if item != '']

    def float_list(self, value: Union[str, list[float], float], sep: str = ',') -> list[float]:
        if isinstance(value, float):
            return [value]
        elif isinstance(value, list):
            return [self.float(value=item) for item in value]
        elif isinstance(value, str):
            value_list = value.split(sep)
            return [self.float(value=item) for item in value_list if item != '']

    def str_list(self, value: Union[str, list[str], float], sep: str = ',') -> list[str]:
        if isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            return [self.render(value=item) for item in value]
        elif isinstance(value, str):
            value_list = value.split(sep)
            return [self.render(value=item) for item in value_list if item != '']

    def str(self, value: str):
        return self.render(value)

    def render(self, value: str) -> str:
        if '{{' not in value or '}}' not in value:
            return value

        for i in range(3):
            # 最多嵌套3层
            rendered_value = jinja2.Template(value).render(
                    self.node.context, math=math, random=random,
                    name=self.node.name)
            if '{{' not in rendered_value or '}}' not in rendered_value:
                return rendered_value
            if rendered_value == value:
                return rendered_value
            value = rendered_value
        return value

    def list(self, value: typing.Any) -> typing.List[typing.Any]:
        if isinstance(value, str):
            return eval(self.render(value))
        elif isinstance(value, list):
            return value
        elif isinstance(value, tuple):
            return list(value)
        else:
            try:
                import numpy
                if isinstance(value, numpy.ndarray):
                    return value.tolist()
            except ImportError:
                pass
            try:
                import torch
                if isinstance(value, torch.Tensor):
                    return value.cpu().tolist()
            except ImportError:
                pass
            raise Exception(f'array error {value}')

    def dict(self, value: typing.Any) -> typing.Dict[str, typing.Any]:
        if isinstance(value, str):
            return self.eval(self.render(value))
        elif isinstance(value, dict):
            return value
        else:
            raise Exception(f'dict error {value}')

    def json_loads(self, value: typing.Any):
        if isinstance(value, str):
            return json.loads(value)
        elif isinstance(value, dict):
            return value
        elif isinstance(value, list):
            return value
        elif isinstance(value, tuple):
            return value
        else:
            try:
                import numpy
                if isinstance(value, numpy.ndarray):
                    return value
            except ImportError:
                pass
            raise Exception(f'json loads error {value}')
