from stable_baselines3.common.logger import configure, Logger, make_output_format
from typing import Any
from collections import defaultdict


class TensorboardLogger(Logger):

    def __init__(self, folder: str, verbose: int):
        log_suffix = ''
        format_strings = ["stdout", "tensorboard"] if verbose == 1 else ['tensorboard']
        output_formats = [make_output_format(f, folder, log_suffix) for f in format_strings]
        super().__init__(folder, output_formats=output_formats)
        self.old_name_to_value = { }
        self.name_to_count = defaultdict(float)

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
        old_value = self.old_name_to_value.get(key, 0)
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
        old_value = self.old_name_to_value.get(key, 0)
        self.record(key, value + old_value)

    def dump(self, step: int = 0) -> None:
        self.old_name_to_value = self.name_to_value.copy()
        super().dump(step=step)
