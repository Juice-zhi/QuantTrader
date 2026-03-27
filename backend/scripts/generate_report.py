"""
QuantTrader 综合回测报告生成器

对所有 10 个策略在不同时间周期和仓位大小下进行回测，
生成完整的对比报告。
"""
import sys
import json
import time
from datetime import datetime

import requests

API = "http://127.0.0.1:8000"

# ── 配置 ──

STRATEGIES = [
    "MeanReversionStrategy",
    "MomentumBreakoutStrategy",
    "FactorComboStrategy",
    "GridTradingStrategy",
    "DualMAStrategy",
    "PriceActionStrategy",
    "ICTStrategy",
    "TrendFollowingStrategy",
    "SupertrendStrategy",
    "BreakoutPullbackStrategy",
]

# 测试不同时间周期
TIMEFRAMES = ["1h", "4h", "1d"]

# 测试不同初始资金 (代表不同仓位大小)
CAPITAL_SIZES = [
    ("Small ($10k)", 10000),
    ("Medium ($100k)", 100000),
    ("Large ($500k)", 500000),
]

SYMBOL = "BTC/USDT"
EXCHANGE = "binance"


def run_backtest(strategy_type, timeframe, capital, params=None):
    """执行单次回测"""
    body = {
        "strategy_type": strategy_type,
        "symbol": SYMBOL,
        "timeframe": timeframe,
        "exchange": EXCHANGE,
        "initial_capital": capital,
        "params": params or {},
    }
    try:
        resp = requests.post(f"{API}/api/backtest/run", json=body, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": resp.text[:200]}
    except Exception as e:
        return {"error": str(e)}


def format_pct(v):
    if v is None:
        return "N/A"
    return f"{v * 100:+.2f}%" if v >= 0 else f"{v * 100:.2f}%"


def format_ratio(v):
    if v is None:
        return "N/A"
    return f"{v:.2f}"


def get_strategy_name(strategy_type):
    """从API获取策略中文名"""
    resp = requests.get(f"{API}/api/strategies/types")
    for s in resp.json().get("strategies", []):
        if s.get("class_name") == strategy_type or s.get("name") == strategy_type:
            return s["name"]
    return strategy_type


def main():
    print("=" * 100)
    print(f"  QuantTrader 综合回测报告")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  标的: {SYMBOL} | 交易所: {EXCHANGE}")
    print("=" * 100)

    # 获取策略名称映射
    resp = requests.get(f"{API}/api/strategies/types")
    name_map = {}
    for s in resp.json().get("strategies", []):
        # Try matching by class name format
        for strat in STRATEGIES:
            if strat.lower() in s.get("name", "").lower() or s.get("name", "") in strat:
                name_map[strat] = s["name"]
    # 如果映射不上就用类名
    for strat in STRATEGIES:
        if strat not in name_map:
            name_map[strat] = strat

    all_results = []
    total_tests = len(STRATEGIES) * len(TIMEFRAMES) * len(CAPITAL_SIZES)
    done = 0

    # ─────────────────────────────────────────
    # Part 1: 按时间周期对比 (固定 $100k)
    # ─────────────────────────────────────────
    print("\n")
    print("━" * 100)
    print("  PART 1: 策略 × 时间周期 对比 (初始资金: $100,000)")
    print("━" * 100)

    for tf in TIMEFRAMES:
        print(f"\n  ▸ Timeframe: {tf}")
        print(f"  {'策略':<22} {'总收益':>10} {'年化收益':>10} {'夏普比率':>8} {'最大回撤':>10} {'胜率':>8} {'盈亏比':>8} {'交易次数':>8}")
        print("  " + "─" * 90)

        for strat in STRATEGIES:
            done += 1
            sys.stdout.write(f"\r  [{done}/{total_tests}] Running {strat} on {tf}...")
            sys.stdout.flush()

            result = run_backtest(strat, tf, 100000)

            if "error" in result:
                print(f"\r  {name_map[strat]:<22} {'ERROR':>10}")
                all_results.append({
                    "strategy": strat, "name": name_map[strat],
                    "timeframe": tf, "capital": 100000,
                    "error": result["error"],
                })
                continue

            m = result.get("metrics", {})
            row = {
                "strategy": strat,
                "name": name_map[strat],
                "timeframe": tf,
                "capital": 100000,
                "total_return": m.get("total_return", 0),
                "annual_return": m.get("annual_return", 0),
                "sharpe_ratio": m.get("sharpe_ratio", 0),
                "max_drawdown": m.get("max_drawdown", 0),
                "win_rate": m.get("win_rate", 0),
                "profit_factor": m.get("profit_factor", 0),
                "total_trades": m.get("total_trades", 0),
                "volatility": m.get("volatility", 0),
            }
            all_results.append(row)

            print(
                f"\r  {name_map[strat]:<22}"
                f" {format_pct(row['total_return']):>10}"
                f" {format_pct(row['annual_return']):>10}"
                f" {format_ratio(row['sharpe_ratio']):>8}"
                f" {format_pct(-row['max_drawdown']):>10}"
                f" {row['win_rate']*100:>7.1f}%"
                f" {format_ratio(row['profit_factor']):>8}"
                f" {row['total_trades']:>8}"
            )

    # ─────────────────────────────────────────
    # Part 2: 按仓位大小对比 (固定 1d)
    # ─────────────────────────────────────────
    print("\n\n")
    print("━" * 100)
    print("  PART 2: 策略 × 仓位大小 对比 (时间周期: 1d)")
    print("━" * 100)

    for cap_name, cap_val in CAPITAL_SIZES:
        if cap_val == 100000:
            # 已经在Part1中跑过了
            done += len(STRATEGIES)
            continue

        print(f"\n  ▸ Capital: {cap_name}")
        print(f"  {'策略':<22} {'总收益':>10} {'最终资金':>14} {'夏普比率':>8} {'最大回撤':>10} {'交易次数':>8}")
        print("  " + "─" * 76)

        for strat in STRATEGIES:
            done += 1
            sys.stdout.write(f"\r  [{done}/{total_tests}] Running {strat} with {cap_name}...")
            sys.stdout.flush()

            result = run_backtest(strat, "1d", cap_val)

            if "error" in result:
                print(f"\r  {name_map[strat]:<22} {'ERROR':>10}")
                all_results.append({
                    "strategy": strat, "name": name_map[strat],
                    "timeframe": "1d", "capital": cap_val,
                    "error": result["error"],
                })
                continue

            m = result.get("metrics", {})
            final_cap = cap_val * (1 + m.get("total_return", 0))
            row = {
                "strategy": strat,
                "name": name_map[strat],
                "timeframe": "1d",
                "capital": cap_val,
                "total_return": m.get("total_return", 0),
                "annual_return": m.get("annual_return", 0),
                "sharpe_ratio": m.get("sharpe_ratio", 0),
                "max_drawdown": m.get("max_drawdown", 0),
                "win_rate": m.get("win_rate", 0),
                "profit_factor": m.get("profit_factor", 0),
                "total_trades": m.get("total_trades", 0),
                "final_capital": final_cap,
            }
            all_results.append(row)

            print(
                f"\r  {name_map[strat]:<22}"
                f" {format_pct(row['total_return']):>10}"
                f" ${final_cap:>13,.2f}"
                f" {format_ratio(row['sharpe_ratio']):>8}"
                f" {format_pct(-row['max_drawdown']):>10}"
                f" {row['total_trades']:>8}"
            )

    # ─────────────────────────────────────────
    # Part 3: 综合排名
    # ─────────────────────────────────────────
    print("\n\n")
    print("━" * 100)
    print("  PART 3: 综合排名 (基于1d周期, $100k)")
    print("━" * 100)

    daily_100k = [r for r in all_results
                  if r.get("timeframe") == "1d"
                  and r.get("capital") == 100000
                  and "error" not in r
                  and r.get("total_trades", 0) > 0]

    if daily_100k:
        # Sort by Sharpe ratio
        by_sharpe = sorted(daily_100k, key=lambda x: x.get("sharpe_ratio", 0), reverse=True)
        print("\n  📊 按夏普比率排名:")
        for i, r in enumerate(by_sharpe, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"  {medal} #{i} {r['name']:<22} Sharpe={r['sharpe_ratio']:.2f}  Return={r['total_return']*100:+.2f}%  DD={r['max_drawdown']*100:.2f}%")

        # Sort by total return
        by_return = sorted(daily_100k, key=lambda x: x.get("total_return", 0), reverse=True)
        print(f"\n  💰 按总收益排名:")
        for i, r in enumerate(by_return, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"  {medal} #{i} {r['name']:<22} Return={r['total_return']*100:+.2f}%  Sharpe={r['sharpe_ratio']:.2f}  Trades={r['total_trades']}")

        # Sort by risk-adjusted (Sharpe > 0.5 and lowest drawdown)
        quality = [r for r in daily_100k if r.get("sharpe_ratio", 0) > 0.3]
        if quality:
            by_quality = sorted(quality, key=lambda x: x.get("max_drawdown", 1))
            print(f"\n  🛡️ 最佳风险调整收益 (Sharpe>0.3, 按最小回撤排):")
            for i, r in enumerate(by_quality, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
                print(f"  {medal} #{i} {r['name']:<22} DD={r['max_drawdown']*100:.2f}%  Sharpe={r['sharpe_ratio']:.2f}  Return={r['total_return']*100:+.2f}%")

    # ─────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────
    total_run = len([r for r in all_results if "error" not in r])
    total_err = len([r for r in all_results if "error" in r])
    print("\n")
    print("=" * 100)
    print(f"  报告完成 | 成功: {total_run} | 失败: {total_err} | 总计: {total_run + total_err}")
    print(f"  注: 回测基于历史数据，不代表未来表现。手续费=0.1%, 滑点=0.05%")
    print("=" * 100)

    # Save JSON
    output_path = "/Users/guozhi/Agent/QuantTrader/backend/data/backtest_report.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  📁 详细数据已保存: {output_path}")


if __name__ == "__main__":
    main()
