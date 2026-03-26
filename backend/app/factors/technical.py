"""
技术因子 - 经典技术分析指标

包含:
- SMA (简单移动平均)
- EMA (指数移动平均)
- RSI (相对强弱指数)
- MACD (异同移动平均)
- BollingerBands (布林带)
- ATR (真实波幅)
- StochasticOscillator (随机指标/KDJ)
- WilliamsR (威廉指标)
- CCI (顺势指标)
"""
import pandas as pd
import numpy as np

from app.factors.base import BaseFactor
from app.factors.registry import FactorRegistry


@FactorRegistry.register
class SMA(BaseFactor):
    """简单移动平均线"""
    category = "technical"
    description = "Simple Moving Average - 最近N个周期收盘价的算术平均"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(window=self.period).mean()


@FactorRegistry.register
class EMA(BaseFactor):
    """指数移动平均线"""
    category = "technical"
    description = "Exponential Moving Average - 给予近期价格更高权重的移动平均"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].ewm(span=self.period, adjust=False).mean()


@FactorRegistry.register
class RSI(BaseFactor):
    """相对强弱指数"""
    category = "technical"
    description = "Relative Strength Index - 衡量价格变动速率和幅度, 0-100之间"

    def __init__(self, period: int = 14):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1/self.period, min_periods=self.period).mean()
        avg_loss = loss.ewm(alpha=1/self.period, min_periods=self.period).mean()

        rs = avg_gain / avg_loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        return rsi


@FactorRegistry.register
class MACD(BaseFactor):
    """异同移动平均线"""
    category = "technical"
    description = "Moving Average Convergence Divergence - 快慢EMA之差, 常用(12,26,9)"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(fast=fast, slow=slow, signal=signal)
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """返回 MACD 柱状图 (histogram)"""
        ema_fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return histogram

    def compute_full(self, df: pd.DataFrame) -> pd.DataFrame:
        """返回完整 MACD 三条线"""
        ema_fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return pd.DataFrame({
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        })


@FactorRegistry.register
class BollingerBands(BaseFactor):
    """布林带"""
    category = "technical"
    description = "Bollinger Bands - 基于移动平均和标准差的价格通道"

    def __init__(self, period: int = 20, num_std: float = 2.0):
        super().__init__(period=period, num_std=num_std)
        self.period = period
        self.num_std = num_std

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """返回 %B 指标 (价格在布林带中的相对位置, 0-1)"""
        sma = df["close"].rolling(self.period).mean()
        std = df["close"].rolling(self.period).std()
        upper = sma + self.num_std * std
        lower = sma - self.num_std * std
        bandwidth = upper - lower
        pct_b = (df["close"] - lower) / bandwidth.replace(0, np.nan)
        return pct_b

    def compute_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """返回完整布林带"""
        sma = df["close"].rolling(self.period).mean()
        std = df["close"].rolling(self.period).std()
        return pd.DataFrame({
            "middle": sma,
            "upper": sma + self.num_std * std,
            "lower": sma - self.num_std * std,
        })


@FactorRegistry.register
class ATR(BaseFactor):
    """真实波幅"""
    category = "technical"
    description = "Average True Range - 衡量价格波动幅度的指标"

    def __init__(self, period: int = 14):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        high = df["high"]
        low = df["low"]
        prev_close = df["close"].shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        return tr.ewm(alpha=1/self.period, min_periods=self.period).mean()


@FactorRegistry.register
class StochasticOscillator(BaseFactor):
    """随机指标 (KDJ中的K值)"""
    category = "technical"
    description = "Stochastic %K - 当前价格在N日最高最低价区间中的相对位置"

    def __init__(self, k_period: int = 14, d_period: int = 3):
        super().__init__(k_period=k_period, d_period=d_period)
        self.k_period = k_period
        self.d_period = d_period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """返回 %K 值"""
        lowest = df["low"].rolling(self.k_period).min()
        highest = df["high"].rolling(self.k_period).max()
        k = 100 * (df["close"] - lowest) / (highest - lowest).replace(0, np.nan)
        return k

    def compute_full(self, df: pd.DataFrame) -> pd.DataFrame:
        """返回 %K 和 %D"""
        k = self.compute(df)
        d = k.rolling(self.d_period).mean()
        return pd.DataFrame({"k": k, "d": d})


@FactorRegistry.register
class WilliamsR(BaseFactor):
    """威廉指标"""
    category = "technical"
    description = "Williams %R - 类似随机指标, 反映超买超卖, 范围-100到0"

    def __init__(self, period: int = 14):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        highest = df["high"].rolling(self.period).max()
        lowest = df["low"].rolling(self.period).min()
        wr = -100 * (highest - df["close"]) / (highest - lowest).replace(0, np.nan)
        return wr


@FactorRegistry.register
class CCI(BaseFactor):
    """顺势指标"""
    category = "technical"
    description = "Commodity Channel Index - 衡量价格偏离统计平均的程度"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        sma = typical_price.rolling(self.period).mean()
        mad = typical_price.rolling(self.period).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        )
        cci = (typical_price - sma) / (0.015 * mad).replace(0, np.nan)
        return cci
