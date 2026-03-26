"""
动量因子 - 衡量价格趋势强度和方向

包含:
- PriceMomentum (价格动量)
- RateOfChange (变化率)
- RelativeStrength (相对强度)
- MomentumAcceleration (动量加速度)
- TrendStrength (趋势强度ADX)
"""
import pandas as pd
import numpy as np

from app.factors.base import BaseFactor
from app.factors.registry import FactorRegistry


@FactorRegistry.register
class PriceMomentum(BaseFactor):
    """价格动量 - N日收益率"""
    category = "momentum"
    description = "N日价格变化百分比, 正值表示上涨趋势"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].pct_change(periods=self.period)


@FactorRegistry.register
class RateOfChange(BaseFactor):
    """变化率"""
    category = "momentum"
    description = "Rate of Change - 当前价格相对N日前价格的百分比变化 * 100"

    def __init__(self, period: int = 12):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        prev = df["close"].shift(self.period)
        return ((df["close"] - prev) / prev.replace(0, np.nan)) * 100


@FactorRegistry.register
class RelativeStrength(BaseFactor):
    """相对强度 - 短期均线与长期均线之比"""
    category = "momentum"
    description = "短期EMA / 长期EMA, >1表示短期强于长期(上涨趋势)"

    def __init__(self, short_period: int = 10, long_period: int = 50):
        super().__init__(short_period=short_period, long_period=long_period)
        self.short_period = short_period
        self.long_period = long_period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        ema_short = df["close"].ewm(span=self.short_period, adjust=False).mean()
        ema_long = df["close"].ewm(span=self.long_period, adjust=False).mean()
        return ema_short / ema_long.replace(0, np.nan)


@FactorRegistry.register
class MomentumAcceleration(BaseFactor):
    """动量加速度 - 动量的变化率"""
    category = "momentum"
    description = "动量的一阶导数, 正值表示动量正在增强"

    def __init__(self, momentum_period: int = 10, accel_period: int = 5):
        super().__init__(momentum_period=momentum_period, accel_period=accel_period)
        self.momentum_period = momentum_period
        self.accel_period = accel_period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        momentum = df["close"].pct_change(periods=self.momentum_period)
        acceleration = momentum.diff(periods=self.accel_period)
        return acceleration


@FactorRegistry.register
class TrendStrength(BaseFactor):
    """趋势强度 (简化版 ADX)"""
    category = "momentum"
    description = "Average Directional Index - 衡量趋势强度, 不区分方向. >25表示强趋势"

    def __init__(self, period: int = 14):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        high = df["high"]
        low = df["low"]
        prev_high = high.shift(1)
        prev_low = low.shift(1)
        prev_close = df["close"].shift(1)

        # True Range
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # +DM and -DM
        plus_dm = high - prev_high
        minus_dm = prev_low - low
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        # Smoothed
        atr = tr.ewm(alpha=1/self.period, min_periods=self.period).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1/self.period, min_periods=self.period).mean() / atr.replace(0, np.nan)
        minus_di = 100 * minus_dm.ewm(alpha=1/self.period, min_periods=self.period).mean() / atr.replace(0, np.nan)

        # DX and ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(alpha=1/self.period, min_periods=self.period).mean()
        return adx
