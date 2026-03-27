"""
动量突破策略

逻辑: 价格突破N日高点且动量增强时买入, 跌破N日低点时卖出
"""
import pandas as pd
import numpy as np

from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry
from app.factors.momentum import PriceMomentum, TrendStrength
from app.factors.volume import VolumeRatio


@StrategyRegistry.register
class MomentumBreakoutStrategy(BaseStrategy):
    name = "动量突破策略"
    description = "价格突破N日高点+动量确认+放量确认时买入, 跌破N日低点时卖出"
    default_params = {
        "breakout_period": 20,
        "momentum_period": 10,
        "adx_threshold": 25,
        "volume_ratio_threshold": 1.5,
        "stop_loss": 0.05,
    }
    param_descriptions = {
        "breakout_period": "突破周期，计算N日最高价/最低价的回溯天数",
        "momentum_period": "动量计算周期，衡量价格变化速度",
        "adx_threshold": "ADX趋势强度阈值，高于此值确认趋势成立",
        "volume_ratio_threshold": "量比阈值，高于此值确认放量突破",
        "stop_loss": "最大止损比例",
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        momentum = PriceMomentum(period=p["momentum_period"])
        adx = TrendStrength(period=14)
        vol_ratio = VolumeRatio(period=p["breakout_period"])

        mom_values = momentum.compute(df)
        adx_values = adx.compute(df)
        vr_values = vol_ratio.compute(df)

        highest = df["high"].rolling(p["breakout_period"]).max()
        lowest = df["low"].rolling(p["breakout_period"]).min()

        result = df[["timestamp", "close"]].copy()
        result["signal"] = 0
        result["momentum"] = mom_values
        result["adx"] = adx_values
        result["volume_ratio"] = vr_values

        # 买入: 突破N日高点 + 动量为正 + 趋势明确 + 放量
        buy_cond = (
            (df["close"] >= highest.shift(1)) &
            (mom_values > 0) &
            (adx_values > p["adx_threshold"]) &
            (vr_values > p["volume_ratio_threshold"])
        )
        # 卖出: 跌破N日低点
        sell_cond = df["close"] <= lowest.shift(1)

        result.loc[buy_cond, "signal"] = 1
        result.loc[sell_cond, "signal"] = -1

        return result

    def param_space(self) -> dict:
        return {
            "breakout_period": (10, 40, 5),
            "momentum_period": (5, 20, 5),
            "adx_threshold": (20, 35, 5),
            "volume_ratio_threshold": (1.0, 2.5, 0.5),
        }
