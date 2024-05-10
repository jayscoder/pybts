from stable_baselines3.common.logger import configure, Logger, make_output_format
from typing import Any
from collections import defaultdict


class TensorboardLogger(Logger):

    def __init__(self, folder: str, verbose: int):
        log_suffix = ''
        format_strings = ["stdout", "tensorboard"] if verbose == 1 else ['tensorboard']
        output_formats = [make_output_format(f, folder, log_suffix) for f in format_strings]
        super().__init__(folder, output_formats=output_formats)
        self.old_name_to_values = []
        self.name_to_count = defaultdict(float)

    def record_and_mean_n_episodes(self, key: str, value: Any, n: int):
        self.record(key=key, value=value)
        self.record_mean_last_n_episodes(key=key, n=n)

    def record_mean_last_n_episodes(self, key: str, n: int, to_key: str = '') -> None:
        """计算过去N轮的平均"""
        if to_key == '':
            to_key = key + f'_{n}_avg'

        if len(self.old_name_to_values) >= n:
            values = self.old_name_to_values[-n:]
        else:
            values = self.old_name_to_values
        v = 0
        for i in range(len(values)):
            v += values[i].get(key, 0)

        if len(values) > 0:
            self.record(to_key, v / len(values))

    def record_mean_weighted(self, key: str, value: Any, weight: float = 1) -> None:
        """
        The same as record(), but if called many times, values averaged.

        :param key: save to log this key
        :param value: save to log this value
        :param weight: 每个平均数的权重，也可以理解为新增的权重，默认是1
        """
        if value is None:
            return
        old_val, old_weight = self.name_to_value[key], self.name_to_count[key]
        new_weight = old_weight + weight
        if new_weight == 0:
            return
        self.name_to_value[key] = (old_val * old_weight + value) / new_weight
        self.name_to_count[key] = weight

    def record_sum(self, key: str, value: Any) -> None:
        """
        The same as record(), but if called many times, values accumulated.

        :param key: save to log this key
        :param value: save to log this value
        """
        if value is None:
            return
        self.name_to_value[key] += value

    def record_minus_old(self, key: str, value: Any) -> None:
        """
        Log a value of some diagnostic
        Call this once for each diagnostic quantity, each iteration
        If called many times, last value will be used.

        :param key: save to log this key
        :param value: save to log this value
        """
        if value is None:
            return
        if len(self.old_name_to_values) > 0:
            old_value = self.old_name_to_values[-1].get(key, 0)
        else:
            old_value = 0
        self.record(key, value - old_value)

    def record_sum_old(self, key: str, value: Any) -> None:
        """
        Log a value of some diagnostic
        Call this once for each diagnostic quantity, each iteration
        If called many times, last value will be used.

        :param key: save to log this key
        :param value: save to log this value
        """
        if value is None:
            return
        if len(self.old_name_to_values) > 0:
            old_value = self.old_name_to_values[-1].get(key, 0)
        else:
            old_value = 0
        self.record(key, value + old_value)

    def dump(self, step: int = 0) -> None:
        self.old_name_to_values.append(self.name_to_value.copy())
        if len(self.old_name_to_values) > 1000:
            # 最多保存最近1000轮数据
            self.old_name_to_values = self.old_name_to_values[-1000:]
        super().dump(step=step)

