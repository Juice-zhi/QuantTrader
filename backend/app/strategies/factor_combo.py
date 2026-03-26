"""
多因子组合策略 - 基于因子库打分

逻辑: 多个因子加权打分, 分数超过阈值买入, 低于阈值卖出
"""
import pandas as pd
import numpy as np

from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry
from app.factors.technical import RSI, MACD
from app.factors.momentum import PriceMomentum, RelativeStrength
from app.factors.volatility import VolatilityRatio
from app.factors.volume import MoneyFlowIndex, VolumeRatio
from app.factors.composite import MultiFactorScore


@StrategyRegistry.register
class FactorComboStrategy(BaseStrategy):
    name = "多因子组合策略"
    description = "RSI+MACD+动量+MFI+量比 五因子加权打分, 综合评分超阈值买入"
    default_params = {
        "rsi_period": 14,
        "momentum_period": 20,
        "mfi_period": 14,
        "buy_threshold": 0.5,
        "sell_threshold": -0.5,
        "weights": [0.25, 0.20, 0.20, 0.20, 0.15],
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params

        factors = [
            RSI(period=p["rsi_period"]),
            MACD(fast=12, slow=26, signal=9),
            PriceMomentum(period=p["momentum_period"]),
            MoneyFlowIndex(period=p["mfi_period"]),
            VolumeRatio(period=20),
        ]

        scorer = MultiFactorScore(factors=factors, weights=p["weights"])
        score = scorer.compute(df)

        result = df[["timestamp", "close"]].copy()
        result["signal"] = 0
        result["factor_score"] = score

        # 各因子值 (用于前端展示)
        for factor in factors:
            result[factor.name] = factor.compute(df)

        result.loc[score > p["buy_threshold"], "signal"] = 1
        result.loc[score < p["sell_threshold"], "signal"] = -1

        return result

    def param_space(self) -> dict:
        return {
            "buy_threshold": (0.2, 1.0, 0.1),
            "sell_threshold": (-1.0, -0.2, 0.1),
        }
