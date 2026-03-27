"""
价格行为学策略 (Price Action)

量化经典K线形态:
- Pin Bar (锤子线/射击之星): 长影线+小实体，反转信号
- Engulfing (吞没形态): 大阳/大阴完全包裹前一根K线
- Inside Bar (内包线): 当前K线完全在前一根范围内，突破方向入场
"""
import pandas as pd
import numpy as np

from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry
from app.factors.technical import ATR, EMA


@StrategyRegistry.register
class PriceActionStrategy(BaseStrategy):
    name = "价格行为策略"
    description = "识别Pin Bar、吞没形态、内包线等经典K线形态，结合趋势滤波和ATR止损"
    default_params = {
        "trend_ema": 50,
        "atr_period": 14,
        "atr_sl_mult": 1.5,
        "pin_bar_ratio": 2.0,      # 影线/实体比 >= 2 判定为pin bar
        "body_pct_max": 0.35,       # pin bar实体占比 <= 35%
        "engulf_min_ratio": 1.2,    # 吞没实体比 >= 1.2
        "stop_loss": 0.04,
    }
    param_descriptions = {
        "trend_ema": "趋势滤波EMA周期，用于判断当前趋势方向",
        "atr_period": "ATR平均真实波幅计算周期",
        "atr_sl_mult": "ATR止损倍数，止损距离 = ATR × 此倍数",
        "pin_bar_ratio": "Pin Bar影线与实体比阈值，影线/实体 ≥ 此值判定为Pin Bar",
        "body_pct_max": "Pin Bar实体占比上限，实体占K线总长比例 ≤ 此值",
        "engulf_min_ratio": "吞没形态实体比阈值，当前实体/前一根实体 ≥ 此值",
        "stop_loss": "最大止损比例",
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        result = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        result["signal"] = 0

        ema_vals = EMA(period=p["trend_ema"]).compute(df)
        atr_vals = ATR(period=p["atr_period"]).compute(df)
        result["ema_trend"] = ema_vals
        result["atr"] = atr_vals

        o, h, l, c = df["open"], df["high"], df["low"], df["close"]
        body = (c - o).abs()
        upper_wick = h - pd.concat([c, o], axis=1).max(axis=1)
        lower_wick = pd.concat([c, o], axis=1).min(axis=1) - l
        candle_range = h - l

        # ── Pin Bar ──
        body_pct = body / candle_range.replace(0, np.nan)
        # 看涨pin bar: 长下影线, 小实体, 收在上半部
        bullish_pin = (
            (lower_wick >= body * p["pin_bar_ratio"]) &
            (body_pct <= p["body_pct_max"]) &
            (c > (h + l) / 2)  # 收盘在上半部
        )
        # 看跌pin bar: 长上影线, 小实体, 收在下半部
        bearish_pin = (
            (upper_wick >= body * p["pin_bar_ratio"]) &
            (body_pct <= p["body_pct_max"]) &
            (c < (h + l) / 2)
        )

        # ── Engulfing ──
        prev_body = body.shift(1)
        prev_o, prev_c = o.shift(1), c.shift(1)
        # 看涨吞没: 前阴后阳, 阳线实体完全包裹阴线
        bullish_engulf = (
            (prev_c < prev_o) &  # 前一根是阴线
            (c > o) &             # 当前阳线
            (body >= prev_body * p["engulf_min_ratio"]) &
            (o <= prev_c) & (c >= prev_o)
        )
        # 看跌吞没
        bearish_engulf = (
            (prev_c > prev_o) &
            (c < o) &
            (body >= prev_body * p["engulf_min_ratio"]) &
            (o >= prev_c) & (c <= prev_o)
        )

        # ── Inside Bar ──
        prev_h, prev_l = h.shift(1), l.shift(1)
        is_inside = (h <= prev_h) & (l >= prev_l)
        # 突破方向
        inside_break_up = is_inside.shift(1).fillna(False) & (c > h.shift(1))
        inside_break_down = is_inside.shift(1).fillna(False) & (c < l.shift(1))

        # ── 趋势滤波 ──
        uptrend = c > ema_vals
        downtrend = c < ema_vals

        # ── 综合信号 ──
        buy_signal = (
            ((bullish_pin | bullish_engulf | inside_break_up) & uptrend)
        )
        sell_signal = (
            ((bearish_pin | bearish_engulf | inside_break_down) & downtrend)
        )

        result.loc[buy_signal, "signal"] = 1
        result.loc[sell_signal, "signal"] = -1

        # 标记形态类型
        result["pattern"] = ""
        result.loc[bullish_pin & uptrend, "pattern"] = "bullish_pin"
        result.loc[bearish_pin & downtrend, "pattern"] = "bearish_pin"
        result.loc[bullish_engulf & uptrend, "pattern"] = "bullish_engulf"
        result.loc[bearish_engulf & downtrend, "pattern"] = "bearish_engulf"
        result.loc[inside_break_up & uptrend, "pattern"] = "inside_break_up"
        result.loc[inside_break_down & downtrend, "pattern"] = "inside_break_down"

        return result

    def param_space(self) -> dict:
        return {
            "trend_ema": (20, 100, 10),
            "pin_bar_ratio": (1.5, 3.0, 0.5),
            "engulf_min_ratio": (1.0, 1.5, 0.1),
            "atr_sl_mult": (1.0, 3.0, 0.5),
        }
