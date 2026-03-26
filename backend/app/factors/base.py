"""
因子基类 - 所有因子必须继承此类

设计原则:
1. 统一接口: compute(df) -> pd.Series
2. 自描述: 每个因子包含 name, category, description, params
3. 幂等性: 相同输入总是产生相同输出
"""
from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class BaseFactor(ABC):
    """
    因子基类

    子类必须实现:
        - name: 因子名称 (e.g., "RSI_14")
        - category: 因子分类 (technical, momentum, volatility, volume, composite)
        - compute(df): 计算因子值

    使用:
        factor = RSI(period=14)
        values = factor.compute(ohlcv_df)
    """

    # 子类必须定义
    name: str = ""
    category: str = ""
    description: str = ""

    def __init__(self, **params):
        self.params = params
        # 用参数更新名称 (e.g., RSI -> RSI_14)
        if not self.name:
            self.name = self.__class__.__name__
        if params:
            param_str = "_".join(str(v) for v in params.values())
            self.name = f"{self.__class__.__name__}_{param_str}"

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """
        计算因子值

        Args:
            df: OHLCV DataFrame, 必须包含列: [timestamp, open, high, low, close, volume]

        Returns:
            pd.Series: 因子值序列, 索引与 df 对齐
        """
        raise NotImplementedError

    def compute_with_validation(self, df: pd.DataFrame) -> pd.Series:
        """带输入验证的计算"""
        required_cols = {"open", "high", "low", "close", "volume"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame 缺少列: {missing}")
        if df.empty:
            return pd.Series(dtype=float)
        return self.compute(df)

    def info(self) -> dict:
        """因子元信息"""
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "params": self.params,
        }

    def __repr__(self):
        return f"<Factor: {self.name} [{self.category}]>"
