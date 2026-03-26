"""
双均线策略

逻辑: 短期均线上穿长期均线(金叉)买入, 下穿(死叉)卖出
"""
import pandas as pd

from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry
from app.factors.technical import EMA


@StrategyRegistry.register
class DualMAStrategy(BaseStrategy):
    name = "双均线策略"
    description = "EMA金叉买入, 死叉卖出. 经典趋势跟随策略"
    default_params = {
        "fast_period": 10,
        "slow_period": 30,
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        fast_ema = EMA(period=p["fast_period"]).compute(df)
        slow_ema = EMA(period=p["slow_period"]).compute(df)

        result = df[["timestamp", "close"]].copy()
        result["fast_ema"] = fast_ema
        result["slow_ema"] = slow_ema
        result["signal"] = 0

        # 金叉: 快线从下方穿过慢线
        cross_up = (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))
        # 死叉: 快线从上方穿过慢线
        cross_down = (fast_ema < slow_ema) & (fast_ema.shift(1) >= slow_ema.shift(1))

        result.loc[cross_up, "signal"] = 1
        result.loc[cross_down, "signal"] = -1

        return result

    def param_space(self) -> dict:
        return {
            "fast_period": (5, 20, 5),
            "slow_period": (20, 60, 10),
        }
