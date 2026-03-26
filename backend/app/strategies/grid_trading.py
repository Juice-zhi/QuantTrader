"""
网格交易策略

逻辑: 在设定的价格区间内均匀布置网格, 价格下穿网格线买入, 上穿网格线卖出
"""
import pandas as pd
import numpy as np

from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry


@StrategyRegistry.register
class GridTradingStrategy(BaseStrategy):
    name = "网格交易策略"
    description = "在价格区间内等距设置网格, 每穿越一条网格线执行一次交易, 适合震荡行情"
    default_params = {
        "grid_count": 10,
        "upper_pct": 0.10,   # 上界偏移比例 (基于初始价格)
        "lower_pct": 0.10,   # 下界偏移比例
        "use_atr": True,     # 是否用ATR动态调整网格
        "atr_period": 14,
        "atr_multiplier": 3,
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        result = df[["timestamp", "close"]].copy()
        result["signal"] = 0

        if p.get("use_atr") and len(df) > p["atr_period"]:
            from app.factors.technical import ATR
            atr = ATR(period=p["atr_period"])
            atr_values = atr.compute(df)
            mid_price = df["close"].rolling(p["atr_period"]).mean()
            half_range = atr_values * p["atr_multiplier"]
            upper = mid_price + half_range
            lower = mid_price - half_range
        else:
            initial_price = df["close"].iloc[0]
            upper = pd.Series(initial_price * (1 + p["upper_pct"]), index=df.index)
            lower = pd.Series(initial_price * (1 - p["lower_pct"]), index=df.index)

        # 动态网格
        grid_count = p["grid_count"]

        for i in range(len(df)):
            if pd.isna(upper.iloc[i]) or pd.isna(lower.iloc[i]):
                continue

            grid_step = (upper.iloc[i] - lower.iloc[i]) / grid_count
            if grid_step <= 0:
                continue

            price = df["close"].iloc[i]
            prev_price = df["close"].iloc[i - 1] if i > 0 else price

            # 计算当前价格所在的网格层级
            level = int((price - lower.iloc[i]) / grid_step)
            prev_level = int((prev_price - lower.iloc[i]) / grid_step)

            if level < prev_level:  # 价格下穿网格 -> 买入
                result.iloc[i, result.columns.get_loc("signal")] = 1
            elif level > prev_level:  # 价格上穿网格 -> 卖出
                result.iloc[i, result.columns.get_loc("signal")] = -1

        result["grid_upper"] = upper
        result["grid_lower"] = lower
        return result

    def param_space(self) -> dict:
        return {
            "grid_count": (5, 20, 5),
            "atr_multiplier": (2, 5, 1),
        }
