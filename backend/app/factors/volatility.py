"""
波动率因子 - 衡量价格波动程度

包含:
- HistoricalVolatility (历史波动率)
- ParkinsonVolatility (Parkinson波动率)
- GarmanKlassVolatility (Garman-Klass波动率)
- VolatilitySkew (波动率偏度)
- VolatilityRatio (波动率比率)
"""
import pandas as pd
import numpy as np

from app.factors.base import BaseFactor
from app.factors.registry import FactorRegistry


@FactorRegistry.register
class HistoricalVolatility(BaseFactor):
    """历史波动率"""
    category = "volatility"
    description = "基于对数收益率的标准差, 年化处理"

    def __init__(self, period: int = 20, annualize: int = 252):
        super().__init__(period=period)
        self.period = period
        self.annualize = annualize

    def compute(self, df: pd.DataFrame) -> pd.Series:
        log_returns = np.log(df["close"] / df["close"].shift(1))
        vol = log_returns.rolling(self.period).std() * np.sqrt(self.annualize)
        return vol


@FactorRegistry.register
class ParkinsonVolatility(BaseFactor):
    """Parkinson波动率 - 利用日内最高最低价, 比收盘价波动率更精确"""
    category = "volatility"
    description = "基于High-Low范围的波动率估计, 效率比历史波动率高5倍"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        log_hl = np.log(df["high"] / df["low"])
        factor = 1 / (4 * np.log(2))
        vol = np.sqrt(factor * (log_hl ** 2).rolling(self.period).mean())
        return vol


@FactorRegistry.register
class GarmanKlassVolatility(BaseFactor):
    """Garman-Klass波动率 - 利用OHLC四个价格, 最高效的波动率估计"""
    category = "volatility"
    description = "结合开高低收四价的波动率估计, 理论效率最高"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        log_hl = np.log(df["high"] / df["low"])
        log_co = np.log(df["close"] / df["open"])
        gk = 0.5 * log_hl**2 - (2 * np.log(2) - 1) * log_co**2
        vol = np.sqrt(gk.rolling(self.period).mean())
        return vol


@FactorRegistry.register
class VolatilitySkew(BaseFactor):
    """波动率偏度 - 上涨波动和下跌波动的不对称性"""
    category = "volatility"
    description = "上涨波动率 / 下跌波动率, >1表示上涨波动更大"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        returns = df["close"].pct_change()
        up_vol = returns.where(returns > 0, 0).rolling(self.period).std()
        down_vol = returns.where(returns < 0, 0).abs().rolling(self.period).std()
        return up_vol / down_vol.replace(0, np.nan)


@FactorRegistry.register
class VolatilityRatio(BaseFactor):
    """波动率比率 - 短期波动率 / 长期波动率"""
    category = "volatility"
    description = "短期与长期波动率之比, >1表示短期波动增大(可能变盘)"

    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__(short_period=short_period, long_period=long_period)
        self.short_period = short_period
        self.long_period = long_period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        returns = df["close"].pct_change()
        short_vol = returns.rolling(self.short_period).std()
        long_vol = returns.rolling(self.long_period).std()
        return short_vol / long_vol.replace(0, np.nan)
