"""
Phase 2 测试: 因子库框架 + 所有因子计算正确性
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.factors.registry import FactorRegistry
from app.factors.base import BaseFactor

# 导入所有因子模块 (触发注册)
from app.factors import technical, momentum, volatility, volume, composite
from app.factors.composite import FactorAnalyzer


@pytest.fixture(scope="module")
def sample_ohlcv() -> pd.DataFrame:
    """生成模拟 OHLCV 数据 (100天)"""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="D")

    # 模拟价格: 带有趋势和波动的随机游走
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, n)
    prices = base_price * np.exp(np.cumsum(returns))

    df = pd.DataFrame({
        "timestamp": dates,
        "open": prices * (1 + np.random.uniform(-0.005, 0.005, n)),
        "high": prices * (1 + np.random.uniform(0.005, 0.02, n)),
        "low": prices * (1 - np.random.uniform(0.005, 0.02, n)),
        "close": prices,
        "volume": np.random.uniform(1e6, 5e6, n),
    })
    return df


# ──────── 测试因子注册中心 ────────

class TestFactorRegistry:

    def test_all_factors_registered(self):
        """确认所有因子都已注册"""
        all_factors = FactorRegistry.list_all()
        names = [f["class_name"] for f in all_factors]
        print(f"\n📊 已注册因子 ({len(names)}个): {names}")
        assert len(names) >= 25, f"预期至少25个因子, 实际 {len(names)}"

    def test_categories(self):
        """测试因子分类"""
        cats = FactorRegistry.categories()
        print(f"📂 因子分类: {cats}")
        assert "technical" in cats
        assert "momentum" in cats
        assert "volatility" in cats
        assert "volume" in cats
        assert "composite" in cats

    def test_create_factor(self):
        """测试创建因子实例"""
        rsi = FactorRegistry.create("RSI", period=14)
        assert rsi.name == "RSI_14"
        assert rsi.category == "technical"
        print(f"✅ 创建因子: {rsi}")

    def test_list_by_category(self):
        """测试按分类查询"""
        tech_factors = FactorRegistry.list_by_category("technical")
        print(f"📊 技术因子: {[f['class_name'] for f in tech_factors]}")
        assert len(tech_factors) >= 9


# ──────── 测试技术因子 ────────

class TestTechnicalFactors:

    def test_sma(self, sample_ohlcv):
        sma = FactorRegistry.create("SMA", period=20)
        result = sma.compute(sample_ohlcv)
        assert len(result) == len(sample_ohlcv)
        assert result.iloc[19:].notna().all()  # 前19个是NaN
        assert result.isna().sum() == 19
        print(f"✅ SMA_20: last={result.iloc[-1]:.2f}")

    def test_ema(self, sample_ohlcv):
        ema = FactorRegistry.create("EMA", period=20)
        result = ema.compute(sample_ohlcv)
        assert result.notna().sum() > 80
        print(f"✅ EMA_20: last={result.iloc[-1]:.2f}")

    def test_rsi(self, sample_ohlcv):
        rsi = FactorRegistry.create("RSI", period=14)
        result = rsi.compute(sample_ohlcv)
        valid = result.dropna()
        assert valid.min() >= 0
        assert valid.max() <= 100
        print(f"✅ RSI_14: last={valid.iloc[-1]:.2f}, range=[{valid.min():.1f}, {valid.max():.1f}]")

    def test_macd(self, sample_ohlcv):
        macd = FactorRegistry.create("MACD", fast=12, slow=26, signal=9)
        result = macd.compute(sample_ohlcv)
        assert len(result) == len(sample_ohlcv)
        # MACD histogram should oscillate around 0
        valid = result.dropna()
        assert valid.min() < 0 < valid.max()
        print(f"✅ MACD: last={valid.iloc[-1]:.4f}")

    def test_bollinger_bands(self, sample_ohlcv):
        bb = FactorRegistry.create("BollingerBands", period=20, num_std=2.0)
        pct_b = bb.compute(sample_ohlcv)
        valid = pct_b.dropna()
        # %B should be mostly between 0 and 1 (can exceed)
        assert valid.median() > 0
        assert valid.median() < 1
        print(f"✅ BollingerBands %B: median={valid.median():.3f}")

    def test_atr(self, sample_ohlcv):
        atr = FactorRegistry.create("ATR", period=14)
        result = atr.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid > 0).all()
        print(f"✅ ATR_14: last={valid.iloc[-1]:.4f}")

    def test_stochastic(self, sample_ohlcv):
        stoch = FactorRegistry.create("StochasticOscillator", k_period=14, d_period=3)
        result = stoch.compute(sample_ohlcv)
        valid = result.dropna()
        assert valid.min() >= 0
        assert valid.max() <= 100
        print(f"✅ Stochastic %K: last={valid.iloc[-1]:.2f}")

    def test_williams_r(self, sample_ohlcv):
        wr = FactorRegistry.create("WilliamsR", period=14)
        result = wr.compute(sample_ohlcv)
        valid = result.dropna()
        assert valid.min() >= -100
        assert valid.max() <= 0
        print(f"✅ Williams %R: last={valid.iloc[-1]:.2f}")

    def test_cci(self, sample_ohlcv):
        cci = FactorRegistry.create("CCI", period=20)
        result = cci.compute(sample_ohlcv)
        valid = result.dropna()
        assert len(valid) > 0
        print(f"✅ CCI_20: last={valid.iloc[-1]:.2f}")


# ──────── 测试动量因子 ────────

class TestMomentumFactors:

    def test_price_momentum(self, sample_ohlcv):
        pm = FactorRegistry.create("PriceMomentum", period=20)
        result = pm.compute(sample_ohlcv)
        valid = result.dropna()
        assert len(valid) == len(sample_ohlcv) - 20
        print(f"✅ PriceMomentum_20: last={valid.iloc[-1]:.4f}")

    def test_rate_of_change(self, sample_ohlcv):
        roc = FactorRegistry.create("RateOfChange", period=12)
        result = roc.compute(sample_ohlcv)
        valid = result.dropna()
        assert len(valid) > 0
        print(f"✅ RateOfChange_12: last={valid.iloc[-1]:.2f}%")

    def test_relative_strength(self, sample_ohlcv):
        rs = FactorRegistry.create("RelativeStrength", short_period=10, long_period=50)
        result = rs.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid > 0).all()
        print(f"✅ RelativeStrength: last={valid.iloc[-1]:.4f}")

    def test_momentum_acceleration(self, sample_ohlcv):
        ma = FactorRegistry.create("MomentumAcceleration", momentum_period=10, accel_period=5)
        result = ma.compute(sample_ohlcv)
        valid = result.dropna()
        assert len(valid) > 0
        print(f"✅ MomentumAcceleration: last={valid.iloc[-1]:.6f}")

    def test_trend_strength(self, sample_ohlcv):
        adx = FactorRegistry.create("TrendStrength", period=14)
        result = adx.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid >= 0).all()
        print(f"✅ TrendStrength (ADX): last={valid.iloc[-1]:.2f}")


# ──────── 测试波动率因子 ────────

class TestVolatilityFactors:

    def test_historical_volatility(self, sample_ohlcv):
        hv = FactorRegistry.create("HistoricalVolatility", period=20)
        result = hv.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid >= 0).all()
        print(f"✅ HistoricalVolatility: last={valid.iloc[-1]:.4f}")

    def test_parkinson_volatility(self, sample_ohlcv):
        pv = FactorRegistry.create("ParkinsonVolatility", period=20)
        result = pv.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid >= 0).all()
        print(f"✅ ParkinsonVolatility: last={valid.iloc[-1]:.4f}")

    def test_garman_klass(self, sample_ohlcv):
        gk = FactorRegistry.create("GarmanKlassVolatility", period=20)
        result = gk.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid >= 0).all()
        print(f"✅ GarmanKlassVolatility: last={valid.iloc[-1]:.4f}")

    def test_volatility_skew(self, sample_ohlcv):
        vs = FactorRegistry.create("VolatilitySkew", period=20)
        result = vs.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid > 0).all()
        print(f"✅ VolatilitySkew: last={valid.iloc[-1]:.4f}")

    def test_volatility_ratio(self, sample_ohlcv):
        vr = FactorRegistry.create("VolatilityRatio", short_period=5, long_period=20)
        result = vr.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid > 0).all()
        print(f"✅ VolatilityRatio: last={valid.iloc[-1]:.4f}")


# ──────── 测试量价因子 ────────

class TestVolumeFActors:

    def test_obv(self, sample_ohlcv):
        obv = FactorRegistry.create("OBV")
        result = obv.compute(sample_ohlcv)
        assert len(result) == len(sample_ohlcv)
        print(f"✅ OBV: last={result.iloc[-1]:.0f}")

    def test_vwap(self, sample_ohlcv):
        vwap = FactorRegistry.create("VWAP", period=20)
        result = vwap.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid > 0).all()
        print(f"✅ VWAP_20: last={valid.iloc[-1]:.2f}")

    def test_volume_ratio(self, sample_ohlcv):
        vr = FactorRegistry.create("VolumeRatio", period=20)
        result = vr.compute(sample_ohlcv)
        valid = result.dropna()
        assert (valid > 0).all()
        print(f"✅ VolumeRatio: last={valid.iloc[-1]:.4f}")

    def test_money_flow_index(self, sample_ohlcv):
        mfi = FactorRegistry.create("MoneyFlowIndex", period=14)
        result = mfi.compute(sample_ohlcv)
        valid = result.dropna()
        assert valid.min() >= 0
        assert valid.max() <= 100
        print(f"✅ MFI_14: last={valid.iloc[-1]:.2f}")

    def test_force_index(self, sample_ohlcv):
        fi = FactorRegistry.create("ForceIndex", period=13)
        result = fi.compute(sample_ohlcv)
        valid = result.dropna()
        assert len(valid) > 0
        print(f"✅ ForceIndex_13: last={valid.iloc[-1]:.0f}")

    def test_volume_weighted_momentum(self, sample_ohlcv):
        vwm = FactorRegistry.create("VolumeWeightedMomentum", period=20)
        result = vwm.compute(sample_ohlcv)
        valid = result.dropna()
        assert len(valid) > 0
        print(f"✅ VolumeWeightedMomentum: last={valid.iloc[-1]:.4f}")


# ──────── 测试复合因子与分析工具 ────────

class TestCompositeFactors:

    def test_multi_factor_score(self, sample_ohlcv):
        rsi = FactorRegistry.create("RSI", period=14)
        pm = FactorRegistry.create("PriceMomentum", period=20)
        vr = FactorRegistry.create("VolumeRatio", period=20)

        mfs = composite.MultiFactorScore(
            factors=[rsi, pm, vr],
            weights=[0.4, 0.3, 0.3],
        )
        result = mfs.compute(sample_ohlcv)
        assert len(result) == len(sample_ohlcv)
        print(f"✅ MultiFactorScore: last={result.iloc[-1]:.4f}")

    def test_factor_ic(self, sample_ohlcv):
        rsi = FactorRegistry.create("RSI", period=14)
        factor_values = rsi.compute(sample_ohlcv)
        forward_returns = sample_ohlcv["close"].pct_change(5).shift(-5)

        ic = FactorAnalyzer.compute_ic(factor_values, forward_returns)
        assert -1 <= ic <= 1
        print(f"✅ RSI IC = {ic:.4f}")

    def test_factor_correlation(self, sample_ohlcv):
        rsi = FactorRegistry.create("RSI", period=14)
        macd = FactorRegistry.create("MACD", fast=12, slow=26, signal=9)

        corr = FactorAnalyzer.compute_factor_correlation({
            "RSI": rsi.compute(sample_ohlcv),
            "MACD": macd.compute(sample_ohlcv),
        })
        assert corr.shape == (2, 2)
        assert corr.loc["RSI", "RSI"] == 1.0
        print(f"✅ RSI-MACD相关性: {corr.loc['RSI', 'MACD']:.4f}")

    def test_factor_stats(self, sample_ohlcv):
        rsi = FactorRegistry.create("RSI", period=14)
        values = rsi.compute(sample_ohlcv)
        stats = FactorAnalyzer.compute_factor_stats(values)
        assert "mean" in stats
        assert "std" in stats
        assert stats["count"] == len(sample_ohlcv)
        print(f"✅ RSI统计: mean={stats['mean']:.2f}, std={stats['std']:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-p", "no:warnings"])
