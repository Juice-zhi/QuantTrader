"""
量价因子 - 结合价格和成交量分析

包含:
- OBV (能量潮)
- VWAP (成交量加权平均价)
- VolumeRatio (量比)
- MoneyFlowIndex (资金流量指标)
- ForceIndex (力量指标)
- VolumeWeightedMomentum (量价动量)
"""
import pandas as pd
import numpy as np

from app.factors.base import BaseFactor
from app.factors.registry import FactorRegistry


@FactorRegistry.register
class OBV(BaseFactor):
    """能量潮"""
    category = "volume"
    description = "On-Balance Volume - 根据价格涨跌累加成交量, 量价背离常预示反转"

    def __init__(self):
        super().__init__()

    def compute(self, df: pd.DataFrame) -> pd.Series:
        direction = np.sign(df["close"].diff())
        obv = (direction * df["volume"]).cumsum()
        return obv


@FactorRegistry.register
class VWAP(BaseFactor):
    """成交量加权平均价"""
    category = "volume"
    description = "Volume Weighted Average Price - 用成交量加权的平均价格, 机构常用基准"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        cum_tp_vol = (typical_price * df["volume"]).rolling(self.period).sum()
        cum_vol = df["volume"].rolling(self.period).sum()
        return cum_tp_vol / cum_vol.replace(0, np.nan)


@FactorRegistry.register
class VolumeRatio(BaseFactor):
    """量比 - 当前成交量相对于平均成交量"""
    category = "volume"
    description = "当前量 / N日平均量, >1表示放量, <1表示缩量"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        avg_volume = df["volume"].rolling(self.period).mean()
        return df["volume"] / avg_volume.replace(0, np.nan)


@FactorRegistry.register
class MoneyFlowIndex(BaseFactor):
    """资金流量指标"""
    category = "volume"
    description = "Money Flow Index - 结合价格和成交量的RSI, 超买>80, 超卖<20"

    def __init__(self, period: int = 14):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        raw_money_flow = typical_price * df["volume"]
        tp_diff = typical_price.diff()

        positive_flow = raw_money_flow.where(tp_diff > 0, 0)
        negative_flow = raw_money_flow.where(tp_diff < 0, 0)

        pos_sum = positive_flow.rolling(self.period).sum()
        neg_sum = negative_flow.rolling(self.period).sum()

        mfi = 100 - 100 / (1 + pos_sum / neg_sum.replace(0, np.nan))
        return mfi


@FactorRegistry.register
class ForceIndex(BaseFactor):
    """力量指标"""
    category = "volume"
    description = "Force Index - 价格变化 × 成交量, 衡量多空力量"

    def __init__(self, period: int = 13):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        force = df["close"].diff() * df["volume"]
        return force.ewm(span=self.period, adjust=False).mean()


@FactorRegistry.register
class VolumeWeightedMomentum(BaseFactor):
    """量价动量 - 用成交量加权的价格动量"""
    category = "volume"
    description = "成交量加权的收益率, 放量上涨得分更高"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        returns = df["close"].pct_change()
        vol_weight = df["volume"] / df["volume"].rolling(self.period).mean().replace(0, np.nan)
        weighted_returns = returns * vol_weight
        return weighted_returns.rolling(self.period).sum()
