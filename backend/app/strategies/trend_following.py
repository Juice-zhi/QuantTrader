"""
趋势跟随策略 (日进斗斗金风格)

核心思想: "让利润奔跑，截断亏损"
- 参考油管 "日进斗金" 趋势跟随体系
- 多时间框架趋势确认
- ATR 追踪止损 (让利润奔跑的关键)
- 金字塔加仓 (趋势确认后加仓放大利润)
- 严格风险控制 (单笔最大亏损固定)

交易逻辑:
1. 趋势判断: EMA200 定大方向, EMA50 定中期趋势
2. 入场: 价格突破 EMA 且 ADX > 25 确认趋势启动
3. 追踪止损: 用 ATR 的倍数做 trailing stop
4. 加仓: 趋势持续时在回调后加仓 (金字塔)
"""
import pandas as pd
import numpy as np

from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry
from app.factors.technical import EMA, ATR
from app.factors.momentum import TrendStrength


@StrategyRegistry.register
class TrendFollowingStrategy(BaseStrategy):
    name = "趋势跟随策略"
    description = "日进斗金风格: EMA多级趋势滤波 + ADX趋势强度确认 + ATR追踪止损, 让利润奔跑"
    default_params = {
        "fast_ema": 20,
        "medium_ema": 50,
        "slow_ema": 200,
        "adx_period": 14,
        "adx_threshold": 25,        # ADX > 25 确认强趋势
        "atr_period": 14,
        "atr_trail_mult": 3.0,      # ATR 追踪止损倍数 (核心参数)
        "pullback_ema": 20,          # 回调到此EMA附近视为加仓机会
        "stop_loss": 0.06,           # 最大止损
    }
    param_descriptions = {
        "fast_ema": "快线EMA周期，用于捕捉短期趋势",
        "medium_ema": "中线EMA周期，用于确认中期趋势",
        "slow_ema": "慢线EMA周期，用于判断长期趋势方向",
        "adx_period": "ADX趋势强度指标计算周期",
        "adx_threshold": "ADX阈值，高于此值确认强趋势启动",
        "atr_period": "ATR平均真实波幅计算周期",
        "atr_trail_mult": "ATR追踪止损倍数，止损距离 = ATR × 此倍数（核心参数）",
        "pullback_ema": "回调EMA周期，价格回调到此均线附近视为加仓机会",
        "stop_loss": "最大止损比例",
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        result = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        result["signal"] = 0

        c = df["close"]
        h = df["high"]
        l = df["low"]

        # 多级EMA
        fast = EMA(period=p["fast_ema"]).compute(df)
        medium = EMA(period=p["medium_ema"]).compute(df)
        slow = EMA(period=p["slow_ema"]).compute(df)
        atr = ATR(period=p["atr_period"]).compute(df)
        adx = TrendStrength(period=p["adx_period"]).compute(df)

        result["fast_ema"] = fast
        result["medium_ema"] = medium
        result["slow_ema"] = slow
        result["adx"] = adx
        result["atr"] = atr

        # ── 趋势判定 ──
        # 上升趋势: fast > medium 且价格在medium上方 (放宽条件, slow仅做参考)
        strong_uptrend = (fast > medium) & (c > medium)
        # 下降趋势: fast < medium 且价格在medium下方
        strong_downtrend = (fast < medium) & (c < medium)

        # ADX 趋势强度确认
        trend_confirmed = adx > p["adx_threshold"]

        # ── ATR 追踪止损线 ──
        atr_trail = p["atr_trail_mult"]
        trail_stop_long = pd.Series(np.nan, index=df.index)
        trail_stop_short = pd.Series(np.nan, index=df.index)

        for i in range(1, len(df)):
            # 多头追踪止损: 最高价 - ATR*mult
            atr_val = atr.iloc[i] if pd.notna(atr.iloc[i]) else 0
            new_stop_l = h.iloc[i] - atr_trail * atr_val
            prev_stop_l = trail_stop_long.iloc[i-1]
            if pd.notna(prev_stop_l):
                trail_stop_long.iloc[i] = max(new_stop_l, prev_stop_l) if c.iloc[i] > prev_stop_l else new_stop_l
            else:
                trail_stop_long.iloc[i] = new_stop_l

            # 空头追踪止损
            new_stop_s = l.iloc[i] + atr_trail * atr_val
            prev_stop_s = trail_stop_short.iloc[i-1]
            if pd.notna(prev_stop_s):
                trail_stop_short.iloc[i] = min(new_stop_s, prev_stop_s) if c.iloc[i] < prev_stop_s else new_stop_s
            else:
                trail_stop_short.iloc[i] = new_stop_s

        result["trail_stop_long"] = trail_stop_long
        result["trail_stop_short"] = trail_stop_short

        # ── 入场信号 ──
        # 做多: 强上升趋势 + ADX确认 + 价格在追踪止损线上方
        buy_entry = (
            strong_uptrend &
            trend_confirmed &
            (c > trail_stop_long)
        )
        # 需要去重: 连续信号只取第一个
        buy_signal = buy_entry & (~buy_entry.shift(1).fillna(False))

        # 做空/平仓: 价格跌破追踪止损 或 趋势反转
        sell_signal = (
            (c < trail_stop_long) & (c.shift(1) >= trail_stop_long.shift(1))  # 跌破追踪止损
        ) | (
            strong_downtrend & trend_confirmed  # 趋势反转
        )
        sell_signal = sell_signal & (~sell_signal.shift(1).fillna(False))

        result.loc[buy_signal, "signal"] = 1
        result.loc[sell_signal, "signal"] = -1

        return result

    def param_space(self) -> dict:
        return {
            "fast_ema": (10, 30, 5),
            "medium_ema": (30, 60, 10),
            "slow_ema": (100, 250, 50),
            "adx_threshold": (20, 35, 5),
            "atr_trail_mult": (2.0, 5.0, 0.5),
        }


@StrategyRegistry.register
class SupertrendStrategy(BaseStrategy):
    """
    Supertrend 策略 — 另一种经典趋势跟随

    Supertrend = ATR 通道方向翻转系统
    规则极简但效果惊人
    """
    name = "Supertrend趋势策略"
    description = "基于ATR通道的Supertrend指标: 通道向上做多, 向下做空. 简洁高效的趋势跟随"
    default_params = {
        "atr_period": 10,
        "multiplier": 3.0,
        "trend_filter_ema": 0,  # 0 = 不用趋势滤波 (Supertrend自身就是趋势系统)
        "stop_loss": 0.05,
    }
    param_descriptions = {
        "atr_period": "ATR计算周期，决定Supertrend通道宽度的波动率窗口",
        "multiplier": "ATR倍数，控制Supertrend通道距中轴的距离",
        "trend_filter_ema": "趋势滤波EMA周期，0表示不使用额外趋势滤波",
        "stop_loss": "最大止损比例",
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        result = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        result["signal"] = 0

        h_arr = df["high"].values.astype(float)
        l_arr = df["low"].values.astype(float)
        c_arr = df["close"].values.astype(float)
        atr_s = ATR(period=p["atr_period"]).compute(df)
        atr_arr = atr_s.fillna(0).values.astype(float)
        hl2_arr = (h_arr + l_arr) / 2.0

        mult = p["multiplier"]
        n = len(df)

        # Compute raw bands
        basic_upper = hl2_arr + mult * atr_arr
        basic_lower = hl2_arr - mult * atr_arr

        final_upper = np.copy(basic_upper)
        final_lower = np.copy(basic_lower)
        direction = np.ones(n, dtype=int)  # 1=bullish, -1=bearish
        supertrend = np.zeros(n)

        for i in range(1, n):
            # Lower band ratchet: only goes up (tighter trailing stop for longs)
            if basic_lower[i] > final_lower[i-1] or c_arr[i-1] < final_lower[i-1]:
                final_lower[i] = basic_lower[i]
            else:
                final_lower[i] = final_lower[i-1]

            # Upper band ratchet: only goes down
            if basic_upper[i] < final_upper[i-1] or c_arr[i-1] > final_upper[i-1]:
                final_upper[i] = basic_upper[i]
            else:
                final_upper[i] = final_upper[i-1]

            # Direction flip
            if direction[i-1] == 1:
                # Currently bullish - flip to bearish if close breaks below lower band
                if c_arr[i] < final_lower[i]:
                    direction[i] = -1
                else:
                    direction[i] = 1
            else:
                # Currently bearish - flip to bullish if close breaks above upper band
                if c_arr[i] > final_upper[i]:
                    direction[i] = 1
                else:
                    direction[i] = -1

            supertrend[i] = final_lower[i] if direction[i] == 1 else final_upper[i]

        result["supertrend"] = supertrend
        result["st_direction"] = direction

        # 趋势滤波
        c = df["close"]
        dir_series = pd.Series(direction, index=df.index)

        if p["trend_filter_ema"] > 0:
            trend_ema = EMA(period=p["trend_filter_ema"]).compute(df)
            trend_ok_long = c > trend_ema
            trend_ok_short = c < trend_ema
        else:
            trend_ok_long = pd.Series(True, index=df.index)
            trend_ok_short = pd.Series(True, index=df.index)

        # 信号: 方向翻转
        flip_up = (dir_series == 1) & (dir_series.shift(1) == -1) & trend_ok_long
        flip_down = (dir_series == -1) & (dir_series.shift(1) == 1) & trend_ok_short

        result.loc[flip_up, "signal"] = 1
        result.loc[flip_down, "signal"] = -1

        return result

    def param_space(self) -> dict:
        return {
            "atr_period": (7, 14, 1),
            "multiplier": (2.0, 5.0, 0.5),
            "trend_filter_ema": (0, 200, 50),
        }


@StrategyRegistry.register
class BreakoutPullbackStrategy(BaseStrategy):
    """
    突破回调策略 — 日进斗斗金常用入场方式

    逻辑:
    1. 价格突破N日高点 (趋势启动)
    2. 等待回调到EMA均线附近
    3. 回调触及EMA后再次上涨时入场
    4. ATR追踪止损
    """
    name = "突破回调策略"
    description = "N日突破后等待回调到EMA, 回调结束再入场, 减少追高风险. 配合ATR动态止损"
    default_params = {
        "breakout_period": 20,
        "pullback_ema": 20,
        "atr_period": 14,
        "atr_sl_mult": 2.5,
        "adx_threshold": 20,
        "stop_loss": 0.05,
    }
    param_descriptions = {
        "breakout_period": "突破周期，计算N日最高价/最低价的回溯天数",
        "pullback_ema": "回调EMA周期，价格回调到此均线附近等待再次入场",
        "atr_period": "ATR平均真实波幅计算周期",
        "atr_sl_mult": "ATR止损倍数，动态止损距离 = ATR × 此倍数",
        "adx_threshold": "ADX趋势强度阈值，高于此值确认趋势有效",
        "stop_loss": "最大止损比例",
    }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        result = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        result["signal"] = 0

        c = df["close"]
        h = df["high"]
        l = df["low"]
        bp = p["breakout_period"]

        highest = h.rolling(bp).max()
        lowest = l.rolling(bp).min()
        ema = EMA(period=p["pullback_ema"]).compute(df)
        adx = TrendStrength(period=14).compute(df)

        result["ema"] = ema
        result["adx"] = adx
        result["highest"] = highest
        result["lowest"] = lowest

        # 状态机: 0=无, 1=突破等回调, 2=回调中
        state = 0
        breakout_dir = 0  # 1=多, -1=空

        for i in range(bp + 1, len(df)):
            price = c.iloc[i]
            ema_val = ema.iloc[i]
            adx_val = adx.iloc[i] if pd.notna(adx.iloc[i]) else 0

            if state == 0:
                # 检测突破
                if price > highest.iloc[i-1] and adx_val > p["adx_threshold"]:
                    state = 1
                    breakout_dir = 1
                elif price < lowest.iloc[i-1] and adx_val > p["adx_threshold"]:
                    state = 1
                    breakout_dir = -1

            elif state == 1:
                # 等回调: 价格回到EMA附近
                if breakout_dir == 1 and price <= ema_val * 1.01:
                    state = 2
                elif breakout_dir == -1 and price >= ema_val * 0.99:
                    state = 2
                # 超时重置
                elif abs(i - i) > bp:
                    state = 0

            elif state == 2:
                # 回调结束，再次向突破方向运动 -> 入场
                if breakout_dir == 1 and price > ema_val and c.iloc[i] > c.iloc[i-1]:
                    result.iloc[i, result.columns.get_loc("signal")] = 1
                    state = 0
                elif breakout_dir == -1 and price < ema_val and c.iloc[i] < c.iloc[i-1]:
                    result.iloc[i, result.columns.get_loc("signal")] = -1
                    state = 0

        return result

    def param_space(self) -> dict:
        return {
            "breakout_period": (10, 30, 5),
            "pullback_ema": (10, 30, 5),
            "atr_sl_mult": (1.5, 4.0, 0.5),
            "adx_threshold": (15, 30, 5),
        }
