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
    """

    name: str = ""
    description: str = ""
    default_params: dict = {}

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
        参数搜索空间 (用于参数优化)
        返回 {param_name: (min, max, step)}
        """
        return {}

    def info(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "params": self.params,
            "param_space": self.param_space(),
        }

    def __repr__(self):
        return f"<Strategy: {self.name} params={self.params}>"
