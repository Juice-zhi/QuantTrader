"""
ICT (Inner Circle Trader) 策略

量化 ICT 核心概念:
- Fair Value Gap (FVG): 三根K线中间留下的价格缺口，价格倾向回填
- Order Block (订单块): 大幅移动前的最后一根反向K线，视为机构建仓区
- Liquidity Sweep (流动性扫取): 扫过前高/前低后反转，Smart Money 操作
- Market Structure Shift (结构转换): 高点/低点破坏后的趋势转换

参考: ICT 2022 Mentorship Model
"""
import pandas as pd
import numpy as np

from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry
from app.factors.technical import ATR, EMA


@StrategyRegistry.register
class ICTStrategy(BaseStrategy):
    name = "ICT智能资金策略"
    description = "基于FVG(公允价值缺口)、Order Block(订单块)、流动性扫取的Smart Money策略"
    default_params = {
        "swing_lookback": 10,
        "fvg_min_gap_atr": 0.5,    # FVG最小缺口(ATR倍数)
        "ob_lookback": 20,          # 订单块回溯周期
        "liquidity_lookback": 20,   # 流动性回溯周期
        "trend_ema": 50,
        "atr_period": 14,
        "stop_loss": 0.04,
    }
    param_descriptions = {
        "swing_lookback": "摆动高低点回溯周期，用于识别Swing High/Low",
        "fvg_min_gap_atr": "FVG最小缺口阈值（ATR倍数），缺口 ≥ ATR × 此值才视为有效FVG",
        "ob_lookback": "订单块(Order Block)回溯周期",
        "liquidity_lookback": "流动性扫取回溯周期，检测前N根K线的高低点",
        "trend_ema": "趋势滤波EMA周期，用于判断大方向",
        "atr_period": "ATR平均真实波幅计算周期",
        "stop_loss": "最大止损比例",
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        result = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        result["signal"] = 0

        o, h, l, c = df["open"], df["high"], df["low"], df["close"]
        atr_vals = ATR(period=p["atr_period"]).compute(df)
        ema_vals = EMA(period=p["trend_ema"]).compute(df)
        result["atr"] = atr_vals
        result["ema_trend"] = ema_vals

        n = len(df)
        lb = p["swing_lookback"]

        # ── 1. Swing High / Low 识别 ──
        swing_high = pd.Series(False, index=df.index)
        swing_low = pd.Series(False, index=df.index)
        for i in range(lb, n - lb):
            if h.iloc[i] == h.iloc[i-lb:i+lb+1].max():
                swing_high.iloc[i] = True
            if l.iloc[i] == l.iloc[i-lb:i+lb+1].min():
                swing_low.iloc[i] = True

        # ── 2. Fair Value Gap (FVG) ──
        # 看涨FVG: 第3根K线的low > 第1根K线的high (向上跳空)
        bullish_fvg = pd.Series(False, index=df.index)
        bearish_fvg = pd.Series(False, index=df.index)
        fvg_level = pd.Series(np.nan, index=df.index)

        for i in range(2, n):
            gap_up = l.iloc[i] - h.iloc[i-2]
            gap_down = l.iloc[i-2] - h.iloc[i]
            atr_val = atr_vals.iloc[i] if pd.notna(atr_vals.iloc[i]) else 0

            if gap_up > atr_val * p["fvg_min_gap_atr"] and atr_val > 0:
                bullish_fvg.iloc[i] = True
                fvg_level.iloc[i] = (h.iloc[i-2] + l.iloc[i]) / 2  # FVG中间价

            if gap_down > atr_val * p["fvg_min_gap_atr"] and atr_val > 0:
                bearish_fvg.iloc[i] = True
                fvg_level.iloc[i] = (l.iloc[i-2] + h.iloc[i]) / 2

        # ── 3. Order Block (订单块) ──
        # 看涨OB: 大幅上涨前的最后一根阴线
        bullish_ob = pd.Series(False, index=df.index)
        bearish_ob = pd.Series(False, index=df.index)

        for i in range(1, n):
            atr_val = atr_vals.iloc[i] if pd.notna(atr_vals.iloc[i]) else 0
            if atr_val == 0:
                continue
            move = c.iloc[i] - c.iloc[i-1]
            # 大幅上涨(>1.5 ATR)且前一根是阴线 -> 前一根是看涨OB
            if move > 1.5 * atr_val and c.iloc[i-1] < o.iloc[i-1]:
                bullish_ob.iloc[i-1] = True
            # 大幅下跌且前一根是阳线 -> 前一根是看跌OB
            if move < -1.5 * atr_val and c.iloc[i-1] > o.iloc[i-1]:
                bearish_ob.iloc[i-1] = True

        # ── 4. Liquidity Sweep (流动性扫取) ──
        # 扫过前期高点/低点后反转
        liq_lb = p["liquidity_lookback"]
        sweep_low_reversal = pd.Series(False, index=df.index)
        sweep_high_reversal = pd.Series(False, index=df.index)

        for i in range(liq_lb, n):
            recent_low = l.iloc[i-liq_lb:i].min()
            recent_high = h.iloc[i-liq_lb:i].max()

            # 向下扫过流动性后反转收阳
            if l.iloc[i] < recent_low and c.iloc[i] > o.iloc[i] and c.iloc[i] > (h.iloc[i] + l.iloc[i]) / 2:
                sweep_low_reversal.iloc[i] = True
            # 向上扫过后反转收阴
            if h.iloc[i] > recent_high and c.iloc[i] < o.iloc[i] and c.iloc[i] < (h.iloc[i] + l.iloc[i]) / 2:
                sweep_high_reversal.iloc[i] = True

        # ── 5. 信号整合 ──
        uptrend = c > ema_vals
        downtrend = c < ema_vals

        # 看涨条件: FVG回填/OB区域支撑/流动性扫取反转 + 上升趋势
        buy_conditions = (
            (bullish_fvg | bullish_ob.shift(1).fillna(False) | sweep_low_reversal) &
            uptrend
        )
        # 只在前面有FVG或OB且价格回到该区域时才入场
        # 简化: 直接使用信号
        sell_conditions = (
            (bearish_fvg | bearish_ob.shift(1).fillna(False) | sweep_high_reversal) &
            downtrend
        )

        result.loc[buy_conditions, "signal"] = 1
        result.loc[sell_conditions, "signal"] = -1

        # 标记ICT概念
        result["ict_concept"] = ""
        result.loc[bullish_fvg & uptrend, "ict_concept"] = "bullish_fvg"
        result.loc[bearish_fvg & downtrend, "ict_concept"] = "bearish_fvg"
        result.loc[sweep_low_reversal & uptrend, "ict_concept"] = "sweep_low"
        result.loc[sweep_high_reversal & downtrend, "ict_concept"] = "sweep_high"

        return result

    def param_space(self) -> dict:
        return {
            "swing_lookback": (5, 20, 5),
            "fvg_min_gap_atr": (0.3, 1.0, 0.1),
            "ob_lookback": (10, 30, 5),
            "trend_ema": (20, 100, 20),
        }
