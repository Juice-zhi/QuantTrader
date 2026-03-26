"""
复合因子 - 多因子组合与因子分析工具

包含:
- MultiFactorScore (多因子加权评分)
- FactorIC (因子IC值计算)
- FactorCorrelation (因子相关性)
"""
import pandas as pd
import numpy as np
from typing import Optional

from app.factors.base import BaseFactor
from app.factors.registry import FactorRegistry


@FactorRegistry.register
class MultiFactorScore(BaseFactor):
    """多因子加权评分"""
    category = "composite"
    description = "将多个因子标准化后加权求和, 得到综合评分"

    def __init__(self, factors: Optional[list] = None, weights: Optional[list] = None):
        super().__init__()
        self.factors = factors or []
        self.weights = weights

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """需要预先设置 factors 列表"""
        if not self.factors:
            return pd.Series(0, index=df.index)

        factor_values = []
        for factor in self.factors:
            values = factor.compute(df)
            # Z-Score 标准化
            mean = values.rolling(60, min_periods=20).mean()
            std = values.rolling(60, min_periods=20).std()
            z_score = (values - mean) / std.replace(0, np.nan)
            factor_values.append(z_score)

        if self.weights:
            weights = np.array(self.weights) / sum(self.weights)
        else:
            weights = np.ones(len(factor_values)) / len(factor_values)

        score = pd.Series(0, index=df.index, dtype=float)
        for i, fv in enumerate(factor_values):
            score += weights[i] * fv.fillna(0)

        return score


class FactorAnalyzer:
    """因子分析工具 (非因子类, 是工具类)"""

    @staticmethod
    def compute_ic(
        factor_values: pd.Series,
        forward_returns: pd.Series,
        method: str = "rank",
    ) -> float:
        """
        计算因子 IC (Information Coefficient)

        Args:
            factor_values: 因子值
            forward_returns: 未来N期收益率
            method: "rank" (Rank IC, 默认) 或 "pearson"

        Returns:
            IC值, 范围 [-1, 1]
        """
        valid = pd.DataFrame({
            "factor": factor_values,
            "returns": forward_returns
        }).dropna()

        if len(valid) < 10:
            return 0.0

        if method == "rank":
            return valid["factor"].rank().corr(valid["returns"].rank())
        else:
            return valid["factor"].corr(valid["returns"])

    @staticmethod
    def compute_ic_series(
        factor_values: pd.Series,
        prices: pd.Series,
        forward_period: int = 5,
        rolling_window: int = 60,
    ) -> pd.Series:
        """
        计算滚动 IC 序列

        Args:
            factor_values: 因子值序列
            prices: 收盘价序列
            forward_period: 未来收益的周期
            rolling_window: 滚动窗口大小
        """
        forward_returns = prices.pct_change(periods=forward_period).shift(-forward_period)

        combined = pd.DataFrame({
            "factor": factor_values,
            "returns": forward_returns,
        }).dropna()

        ic_series = combined["factor"].rolling(rolling_window).corr(combined["returns"])
        return ic_series

    @staticmethod
    def compute_factor_correlation(factors_dict: dict[str, pd.Series]) -> pd.DataFrame:
        """
        计算因子间相关性矩阵

        Args:
            factors_dict: {因子名: 因子值Series}

        Returns:
            相关性矩阵 DataFrame
        """
        df = pd.DataFrame(factors_dict)
        return df.corr()

    @staticmethod
    def compute_factor_stats(factor_values: pd.Series) -> dict:
        """计算因子统计信息"""
        return {
            "mean": factor_values.mean(),
            "std": factor_values.std(),
            "min": factor_values.min(),
            "max": factor_values.max(),
            "skew": factor_values.skew(),
            "kurtosis": factor_values.kurtosis(),
            "null_ratio": factor_values.isna().mean(),
            "count": len(factor_values),
        }
