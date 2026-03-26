"""
绩效指标计算

计算回测和实盘交易的完整绩效指标
"""
import pandas as pd
import numpy as np
from typing import Optional


def compute_metrics(
    equity_curve: pd.Series,
    trades: list[dict],
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> dict:
    """
    计算完整绩效指标

    Args:
        equity_curve: 净值序列 (每日)
        trades: 交易记录列表 [{"pnl": ..., "return": ..., ...}]
        risk_free_rate: 无风险利率 (年化)
        periods_per_year: 每年交易日数

    Returns:
        绩效指标字典
    """
    if equity_curve.empty:
        return _empty_metrics()

    returns = equity_curve.pct_change().dropna()
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

    # 年化收益
    n_periods = len(equity_curve)
    years = n_periods / periods_per_year
    annual_return = (1 + total_return) ** (1 / max(years, 0.01)) - 1 if years > 0 else 0

    # 夏普比率 (需要足够的数据点且有波动)
    excess_returns = returns - risk_free_rate / periods_per_year
    sharpe = (
        np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std()
        if len(excess_returns) > 5 and excess_returns.std() > 1e-10 else 0
    )

    # 最大回撤
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    max_drawdown = abs(drawdown.min())

    # Calmar比率
    calmar = annual_return / max_drawdown if max_drawdown > 0 else 0

    # Sortino比率
    downside = returns[returns < 0]
    downside_std = downside.std() if len(downside) > 0 else 0
    sortino = (
        np.sqrt(periods_per_year) * (returns.mean() - risk_free_rate / periods_per_year) / downside_std
        if downside_std > 0 else 0
    )

    # 交易统计
    trade_pnls = [t.get("pnl", 0) for t in trades]
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]

    win_rate = len(wins) / len(trades) if trades else 0
    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 0
    profit_factor = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else (0 if not wins else 999.99)

    # 最大连续亏损
    max_consecutive_losses = _max_consecutive(trade_pnls, negative=True)
    max_consecutive_wins = _max_consecutive(trade_pnls, negative=False)

    return {
        "total_return": round(total_return, 6),
        "annual_return": round(annual_return, 6),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "calmar_ratio": round(calmar, 4),
        "max_drawdown": round(max_drawdown, 6),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_consecutive_wins": max_consecutive_wins,
        "max_consecutive_losses": max_consecutive_losses,
        "volatility": round(returns.std() * np.sqrt(periods_per_year), 6) if len(returns) > 0 else 0,
    }


def _max_consecutive(values: list, negative: bool = True) -> int:
    """计算最大连续正/负数长度"""
    max_count = 0
    count = 0
    for v in values:
        if (negative and v < 0) or (not negative and v > 0):
            count += 1
            max_count = max(max_count, count)
        else:
            count = 0
    return max_count


def _empty_metrics() -> dict:
    return {
        "total_return": 0, "annual_return": 0, "sharpe_ratio": 0,
        "sortino_ratio": 0, "calmar_ratio": 0, "max_drawdown": 0,
        "win_rate": 0, "profit_factor": 0, "total_trades": 0,
        "winning_trades": 0, "losing_trades": 0, "avg_win": 0,
        "avg_loss": 0, "max_consecutive_wins": 0, "max_consecutive_losses": 0,
        "volatility": 0,
    }
