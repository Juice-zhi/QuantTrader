"""
均值回归策略 - 基于布林带

逻辑: 价格跌破下轨买入(超卖反弹), 涨破上轨卖出(超买回落)
"""
import pandas as pd

from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry
from app.factors.technical import BollingerBands, RSI


@StrategyRegistry.register
class MeanReversionStrategy(BaseStrategy):
    name = "均值回归策略"
    description = "基于布林带的均值回归: 价格低于下轨且RSI超卖时买入, 价格高于上轨且RSI超买时卖出"
    default_params = {
        "bb_period": 20,
        "bb_std": 2.0,
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "stop_loss": 0.05,
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        bb = BollingerBands(period=p["bb_period"], num_std=p["bb_std"])
        rsi = RSI(period=p["rsi_period"])

        bands = bb.compute_bands(df)
        rsi_values = rsi.compute(df)

        result = df[["timestamp", "close"]].copy()
        result["signal"] = 0
        result["bb_upper"] = bands["upper"]
        result["bb_lower"] = bands["lower"]
        result["bb_middle"] = bands["middle"]
        result["rsi"] = rsi_values

        # 买入: 价格 < 下轨 且 RSI < 超卖线
        buy_cond = (df["close"] < bands["lower"]) & (rsi_values < p["rsi_oversold"])
        # 卖出: 价格 > 上轨 且 RSI > 超买线
        sell_cond = (df["close"] > bands["upper"]) & (rsi_values > p["rsi_overbought"])

        result.loc[buy_cond, "signal"] = 1
        result.loc[sell_cond, "signal"] = -1

        return result

    def param_space(self) -> dict:
        return {
            "bb_period": (10, 50, 5),
            "bb_std": (1.5, 3.0, 0.5),
            "rsi_period": (7, 21, 7),
            "rsi_oversold": (20, 40, 5),
            "rsi_overbought": (60, 80, 5),
        }
