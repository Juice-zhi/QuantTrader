"""
策略基类 - 所有策略必须继承此类

信号约定:
    1  = 买入信号
   -1  = 卖出信号
    0  = 无操作
"""
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from app.factors.registry import FactorRegistry


class BaseStrategy(ABC):
    """
    策略基类

    子类必须实现:
        - name: 策略名称
        - description: 策略描述
        - default_params: 默认参数字典
        - generate_signals(df): 生成交易信号

    可选:
        - param_space(): 参数搜索范围 {name: (min, max, step)}
        - param_descriptions: 参数描述 {name: "human-readable description"}
        - param_types: 参数类型 {name: "float"|"int"|"bool"|"select"}
    """

    name: str = ""
    description: str = ""
    default_params: dict = {}
    param_descriptions: dict = {}
    param_types: dict = {}  # "float", "int", "bool", "select"
    param_options: dict = {}  # for "select" type: {name: [option1, option2]}

    def __init__(self, **params):
        self.params = {**self.default_params, **params}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            df: OHLCV DataFrame

        Returns:
            DataFrame, 至少包含 'signal' 列 (1=买, -1=卖, 0=持有)
        """
        raise NotImplementedError

    def param_space(self) -> dict[str, tuple]:
        """
        参数搜索空间 (用于参数优化和UI滑块)
        返回 {param_name: (min, max, step)}
        """
        return {}

    def get_param_schema(self) -> list[dict]:
        """
        获取完整参数schema，供前端编辑器使用

        Returns:
            [{
                "key": "trend_ema",
                "label": "Trend EMA Period",
                "type": "float" | "int" | "bool" | "select",
                "default": 50,
                "current": 50,
                "min": 20, "max": 100, "step": 10,  # from param_space
                "options": [],  # for select type
            }, ...]
        """
        space = self.param_space()
        schema = []

        for key, default_val in self.default_params.items():
            current_val = self.params.get(key, default_val)

            # Determine type
            param_type = self.param_types.get(key)
            if not param_type:
                if isinstance(default_val, bool):
                    param_type = "bool"
                elif isinstance(default_val, int) and not isinstance(default_val, bool):
                    param_type = "int"
                elif isinstance(default_val, float):
                    param_type = "float"
                else:
                    param_type = "text"

            entry = {
                "key": key,
                "label": self.param_descriptions.get(key, key.replace("_", " ").title()),
                "type": param_type,
                "default": default_val,
                "current": current_val,
            }

            # Add range from param_space
            if key in space:
                mn, mx, step = space[key]
                entry["min"] = mn
                entry["max"] = mx
                entry["step"] = step

            # Add options for select type
            if key in self.param_options:
                entry["options"] = self.param_options[key]
                entry["type"] = "select"

            schema.append(entry)

        return schema

    def info(self) -> dict:
        return {
            "name": self.name,
            "class_name": self.__class__.__name__,
            "description": self.description,
            "params": self.params,
            "param_space": self.param_space(),
            "param_schema": self.get_param_schema(),
        }

    def __repr__(self):
        return f"<Strategy: {self.name} params={self.params}>"
