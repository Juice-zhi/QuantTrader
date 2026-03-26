"""
回测引擎 - 向量化信号 + 逐bar执行

支持:
- 手续费/滑点模拟
- 止损
- 多空双向
- 完整交易记录
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from app.strategies.base import BaseStrategy
from app.backtest.metrics import compute_metrics


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001     # 手续费率 0.1%
    slippage_rate: float = 0.0005      # 滑点 0.05%
    position_size: float = 1.0         # 仓位比例 (0-1)
    stop_loss: Optional[float] = None  # 止损比例 (e.g., 0.05 = 5%)
    max_positions: int = 1             # 最大持仓数


@dataclass
class TradeRecord:
    """单笔交易记录"""
    entry_date: str
    exit_date: str
    side: str           # "long" or "short"
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    return_pct: float
    commission: float
    exit_reason: str     # "signal" or "stop_loss"


class BacktestEngine:
    """
    回测引擎

    用法:
        engine = BacktestEngine(config)
        result = engine.run(strategy, ohlcv_df)
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()

    def run(self, strategy: BaseStrategy, df: pd.DataFrame) -> dict:
        """
        执行回测

        Args:
            strategy: 策略实例
            df: OHLCV DataFrame

        Returns:
            {
                "metrics": {...},
                "equity_curve": [...],
                "trades": [...],
                "signals_df": DataFrame
            }
        """
        cfg = self.config

        # 1. 生成信号
        signals_df = strategy.generate_signals(df)

        # 2. 逐bar模拟
        cash = cfg.initial_capital
        position = 0.0
        entry_price = 0.0
        entry_date = None

        equity_list = []
        trades = []

        stop_loss = cfg.stop_loss or strategy.params.get("stop_loss")

        for i in range(len(signals_df)):
            row = signals_df.iloc[i]
            price = row["close"]
            signal = row.get("signal", 0)
            date = str(row.get("timestamp", i))

            # 止损检查
            if position > 0 and stop_loss and entry_price > 0:
                loss_pct = (price - entry_price) / entry_price
                if loss_pct < -stop_loss:
                    # 止损平仓
                    sell_price = price * (1 - cfg.slippage_rate)
                    commission = sell_price * position * cfg.commission_rate
                    pnl = (sell_price - entry_price) * position - commission
                    cash += sell_price * position - commission
                    trades.append(TradeRecord(
                        entry_date=entry_date, exit_date=date,
                        side="long", entry_price=entry_price, exit_price=sell_price,
                        quantity=position, pnl=pnl,
                        return_pct=(sell_price / entry_price - 1),
                        commission=commission, exit_reason="stop_loss",
                    ))
                    position = 0.0
                    entry_price = 0.0

            # 信号执行
            if signal == 1 and position == 0:
                # 买入
                buy_price = price * (1 + cfg.slippage_rate)
                invest = cash * cfg.position_size
                commission = invest * cfg.commission_rate
                quantity = (invest - commission) / buy_price
                if quantity > 0:
                    position = quantity
                    entry_price = buy_price
                    entry_date = date
                    cash -= invest

            elif signal == -1 and position > 0:
                # 卖出
                sell_price = price * (1 - cfg.slippage_rate)
                commission = sell_price * position * cfg.commission_rate
                pnl = (sell_price - entry_price) * position - commission
                cash += sell_price * position - commission
                trades.append(TradeRecord(
                    entry_date=entry_date, exit_date=date,
                    side="long", entry_price=entry_price, exit_price=sell_price,
                    quantity=position, pnl=pnl,
                    return_pct=(sell_price / entry_price - 1),
                    commission=commission, exit_reason="signal",
                ))
                position = 0.0
                entry_price = 0.0

            # 记录权益
            equity = cash + position * price
            equity_list.append({
                "date": date,
                "equity": equity,
                "cash": cash,
                "position_value": position * price,
            })

        # 3. 如果还有持仓, 按最后价格平仓
        if position > 0:
            last_price = signals_df.iloc[-1]["close"]
            sell_price = last_price * (1 - cfg.slippage_rate)
            commission = sell_price * position * cfg.commission_rate
            pnl = (sell_price - entry_price) * position - commission
            cash += sell_price * position - commission
            trades.append(TradeRecord(
                entry_date=entry_date,
                exit_date=str(signals_df.iloc[-1].get("timestamp", len(signals_df) - 1)),
                side="long", entry_price=entry_price, exit_price=sell_price,
                quantity=position, pnl=pnl,
                return_pct=(sell_price / entry_price - 1),
                commission=commission, exit_reason="end_of_data",
            ))

        # 4. 计算绩效
        equity_series = pd.Series([e["equity"] for e in equity_list])
        trade_dicts = [
            {"pnl": t.pnl, "return": t.return_pct} for t in trades
        ]
        metrics = compute_metrics(equity_series, trade_dicts)

        return {
            "metrics": metrics,
            "equity_curve": equity_list,
            "trades": [
                {
                    "entry_date": t.entry_date,
                    "exit_date": t.exit_date,
                    "side": t.side,
                    "entry_price": round(t.entry_price, 4),
                    "exit_price": round(t.exit_price, 4),
                    "quantity": round(t.quantity, 6),
                    "pnl": round(t.pnl, 2),
                    "return_pct": round(t.return_pct, 6),
                    "commission": round(t.commission, 2),
                    "exit_reason": t.exit_reason,
                }
                for t in trades
            ],
            "signals_df": signals_df,
            "config": {
                "initial_capital": cfg.initial_capital,
                "commission_rate": cfg.commission_rate,
                "slippage_rate": cfg.slippage_rate,
                "stop_loss": stop_loss,
            },
        }
