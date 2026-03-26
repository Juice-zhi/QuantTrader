"""
Phase 3 测试: 策略引擎 + 回测系统
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入因子 (触发注册)
from app.factors import technical, momentum, volatility, volume, composite

# 导入策略 (触发注册)
from app.strategies import mean_reversion, momentum_strategy, factor_combo, grid_trading, dual_ma
from app.strategies.registry import StrategyRegistry
from app.backtest.engine import BacktestEngine, BacktestConfig
from app.backtest.metrics import compute_metrics


@pytest.fixture(scope="module")
def sample_ohlcv() -> pd.DataFrame:
    """生成200天模拟数据 (足够回测)"""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="D")

    base_price = 100.0
    returns = np.random.normal(0.0005, 0.02, n)
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


# ──────── 测试策略注册 ────────

class TestStrategyRegistry:

    def test_all_strategies_registered(self):
        all_strats = StrategyRegistry.list_all()
        names = [s["name"] for s in all_strats]
        print(f"\n📋 已注册策略 ({len(names)}个): {names}")
        assert len(names) >= 5

    def test_create_strategy(self):
        strat = StrategyRegistry.create("MeanReversionStrategy", bb_period=25)
        assert strat.params["bb_period"] == 25
        print(f"✅ 创建策略: {strat}")


# ──────── 测试信号生成 ────────

class TestSignalGeneration:

    def test_mean_reversion_signals(self, sample_ohlcv):
        strat = StrategyRegistry.create("MeanReversionStrategy")
        signals = strat.generate_signals(sample_ohlcv)
        assert "signal" in signals.columns
        buy_count = (signals["signal"] == 1).sum()
        sell_count = (signals["signal"] == -1).sum()
        print(f"✅ 均值回归: {buy_count}个买入信号, {sell_count}个卖出信号")

    def test_momentum_breakout_signals(self, sample_ohlcv):
        strat = StrategyRegistry.create("MomentumBreakoutStrategy")
        signals = strat.generate_signals(sample_ohlcv)
        assert "signal" in signals.columns
        assert "momentum" in signals.columns
        buy_count = (signals["signal"] == 1).sum()
        sell_count = (signals["signal"] == -1).sum()
        print(f"✅ 动量突破: {buy_count}个买入信号, {sell_count}个卖出信号")

    def test_factor_combo_signals(self, sample_ohlcv):
        strat = StrategyRegistry.create("FactorComboStrategy")
        signals = strat.generate_signals(sample_ohlcv)
        assert "signal" in signals.columns
        assert "factor_score" in signals.columns
        buy_count = (signals["signal"] == 1).sum()
        sell_count = (signals["signal"] == -1).sum()
        print(f"✅ 多因子组合: {buy_count}个买入, {sell_count}个卖出, 因子得分范围=[{signals['factor_score'].min():.2f}, {signals['factor_score'].max():.2f}]")

    def test_grid_trading_signals(self, sample_ohlcv):
        strat = StrategyRegistry.create("GridTradingStrategy")
        signals = strat.generate_signals(sample_ohlcv)
        assert "signal" in signals.columns
        total_signals = (signals["signal"] != 0).sum()
        print(f"✅ 网格交易: {total_signals}个交易信号")

    def test_dual_ma_signals(self, sample_ohlcv):
        strat = StrategyRegistry.create("DualMAStrategy")
        signals = strat.generate_signals(sample_ohlcv)
        assert "signal" in signals.columns
        assert "fast_ema" in signals.columns
        assert "slow_ema" in signals.columns
        buy_count = (signals["signal"] == 1).sum()
        sell_count = (signals["signal"] == -1).sum()
        print(f"✅ 双均线: {buy_count}个金叉, {sell_count}个死叉")


# ──────── 测试回测引擎 ────────

class TestBacktestEngine:

    def test_basic_backtest(self, sample_ohlcv):
        """基本回测功能"""
        config = BacktestConfig(initial_capital=100000, commission_rate=0.001)
        engine = BacktestEngine(config)
        strat = StrategyRegistry.create("DualMAStrategy")

        result = engine.run(strat, sample_ohlcv)

        assert "metrics" in result
        assert "equity_curve" in result
        assert "trades" in result

        m = result["metrics"]
        print(f"\n📊 双均线回测结果:")
        print(f"   总收益: {m['total_return']*100:.2f}%")
        print(f"   年化收益: {m['annual_return']*100:.2f}%")
        print(f"   夏普比率: {m['sharpe_ratio']:.2f}")
        print(f"   最大回撤: {m['max_drawdown']*100:.2f}%")
        print(f"   胜率: {m['win_rate']*100:.1f}%")
        print(f"   盈亏比: {m['profit_factor']:.2f}")
        print(f"   总交易: {m['total_trades']}笔")

        assert len(result["equity_curve"]) == len(sample_ohlcv)
        assert result["equity_curve"][0]["equity"] == 100000

    def test_backtest_with_stop_loss(self, sample_ohlcv):
        """带止损的回测"""
        config = BacktestConfig(
            initial_capital=100000,
            commission_rate=0.001,
            stop_loss=0.03,
        )
        engine = BacktestEngine(config)
        strat = StrategyRegistry.create("MeanReversionStrategy")

        result = engine.run(strat, sample_ohlcv)
        stop_loss_trades = [t for t in result["trades"] if t["exit_reason"] == "stop_loss"]
        print(f"✅ 止损触发 {len(stop_loss_trades)} 次 / 总 {len(result['trades'])} 笔")

    def test_all_strategies_backtest(self, sample_ohlcv):
        """所有策略都能跑完回测"""
        config = BacktestConfig(initial_capital=100000)
        engine = BacktestEngine(config)

        strategy_names = [
            "MeanReversionStrategy",
            "MomentumBreakoutStrategy",
            "FactorComboStrategy",
            "GridTradingStrategy",
            "DualMAStrategy",
        ]

        print(f"\n{'策略':<20} {'总收益':>8} {'夏普':>6} {'回撤':>8} {'胜率':>6} {'交易数':>6}")
        print("-" * 60)

        for name in strategy_names:
            strat = StrategyRegistry.create(name)
            result = engine.run(strat, sample_ohlcv)
            m = result["metrics"]
            print(
                f"{strat.name:<18} "
                f"{m['total_return']*100:>7.2f}% "
                f"{m['sharpe_ratio']:>6.2f} "
                f"{m['max_drawdown']*100:>7.2f}% "
                f"{m['win_rate']*100:>5.1f}% "
                f"{m['total_trades']:>5}"
            )
            # 基本验证
            assert len(result["equity_curve"]) == len(sample_ohlcv)
            assert result["metrics"]["total_trades"] >= 0

        print("✅ 所有策略回测完成")


# ──────── 测试绩效指标计算 ────────

class TestMetrics:

    def test_metrics_calculation(self):
        """测试指标计算正确性"""
        # 构造一个简单的净值曲线
        equity = pd.Series([100, 102, 101, 104, 103, 106, 108, 107, 110, 112])
        trades = [
            {"pnl": 2, "return": 0.02},
            {"pnl": -1, "return": -0.01},
            {"pnl": 3, "return": 0.03},
            {"pnl": -1, "return": -0.01},
            {"pnl": 3, "return": 0.03},
            {"pnl": 2, "return": 0.02},
            {"pnl": -1, "return": -0.01},
            {"pnl": 3, "return": 0.03},
            {"pnl": 2, "return": 0.02},
        ]

        m = compute_metrics(equity, trades)

        assert m["total_return"] > 0
        assert m["win_rate"] > 0.5
        assert m["total_trades"] == 9
        assert m["winning_trades"] == 6
        assert m["losing_trades"] == 3
        assert m["max_drawdown"] > 0
        print(f"✅ 绩效指标: return={m['total_return']*100:.1f}%, sharpe={m['sharpe_ratio']:.2f}, "
              f"win_rate={m['win_rate']*100:.0f}%, max_dd={m['max_drawdown']*100:.1f}%")

    def test_empty_metrics(self):
        """空数据指标"""
        m = compute_metrics(pd.Series(dtype=float), [])
        assert m["total_return"] == 0
        assert m["total_trades"] == 0
        print("✅ 空数据指标正常")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-p", "no:warnings", "-s"])
