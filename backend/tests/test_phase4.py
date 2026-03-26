"""
Phase 4 测试: 交易执行层 (模拟交易 + 执行管理器 + 风控)
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.execution.base import OrderRequest
from app.execution.paper import PaperExchange
from app.execution.manager import ExecutionManager, RiskManager

# 导入策略 (触发注册)
from app.factors import technical, momentum, volatility, volume, composite
from app.strategies import mean_reversion, momentum_strategy, factor_combo, grid_trading, dual_ma
from app.strategies.registry import StrategyRegistry


# ──────── 测试模拟交易所 ────────

class TestPaperExchange:

    @pytest.mark.asyncio
    async def test_market_buy(self):
        """测试市价买入"""
        exchange = PaperExchange(initial_capital=100000)
        exchange.set_price("BTC/USDT", 50000.0)

        request = OrderRequest(
            symbol="BTC/USDT", side="buy",
            order_type="market", quantity=1.0
        )
        response = await exchange.place_order(request)

        assert response.status == "filled"
        assert response.filled_quantity == 1.0
        assert response.filled_price > 50000  # 有滑点
        assert response.fee > 0
        print(f"✅ 买入BTC: price={response.filled_price:.2f}, fee={response.fee:.2f}")

    @pytest.mark.asyncio
    async def test_market_sell(self):
        """测试市价卖出"""
        exchange = PaperExchange(initial_capital=100000)
        exchange.set_price("BTC/USDT", 50000.0)

        # 先买入
        buy_req = OrderRequest(symbol="BTC/USDT", side="buy", order_type="market", quantity=1.0)
        await exchange.place_order(buy_req)

        # 涨价后卖出
        exchange.set_price("BTC/USDT", 55000.0)
        sell_req = OrderRequest(symbol="BTC/USDT", side="sell", order_type="market", quantity=1.0)
        response = await exchange.place_order(sell_req)

        assert response.status == "filled"
        assert exchange.realized_pnl > 0  # 盈利
        print(f"✅ 卖出BTC: pnl={exchange.realized_pnl:.2f}")

    @pytest.mark.asyncio
    async def test_insufficient_funds(self):
        """测试资金不足"""
        exchange = PaperExchange(initial_capital=1000)
        exchange.set_price("BTC/USDT", 50000.0)

        request = OrderRequest(symbol="BTC/USDT", side="buy", order_type="market", quantity=1.0)
        response = await exchange.place_order(request)

        assert response.status == "rejected"
        assert "Insufficient funds" in response.message
        print(f"✅ 资金不足拒绝: {response.message}")

    @pytest.mark.asyncio
    async def test_positions(self):
        """测试持仓查询"""
        exchange = PaperExchange(initial_capital=100000)
        exchange.set_price("BTC/USDT", 50000.0)
        exchange.set_price("ETH/USDT", 3000.0)

        await exchange.place_order(OrderRequest("BTC/USDT", "buy", "market", 0.5))
        await exchange.place_order(OrderRequest("ETH/USDT", "buy", "market", 5.0))

        positions = await exchange.get_positions()
        assert len(positions) == 2
        symbols = {p.symbol for p in positions}
        assert "BTC/USDT" in symbols
        assert "ETH/USDT" in symbols
        print(f"✅ 持仓查询: {len(positions)}个标的")

    @pytest.mark.asyncio
    async def test_account_info(self):
        """测试账户信息"""
        exchange = PaperExchange(initial_capital=100000)
        exchange.set_price("BTC/USDT", 50000.0)
        await exchange.place_order(OrderRequest("BTC/USDT", "buy", "market", 1.0))

        account = await exchange.get_account()
        assert account.total_equity > 0
        assert account.available_cash < 100000  # 花了钱
        assert account.positions_value > 0
        print(f"✅ 账户: equity={account.total_equity:.2f}, cash={account.available_cash:.2f}")

    @pytest.mark.asyncio
    async def test_limit_order(self):
        """测试限价单"""
        exchange = PaperExchange(initial_capital=100000)
        exchange.set_price("BTC/USDT", 50000.0)

        # 限价低于当前价 -> 成交
        req = OrderRequest("BTC/USDT", "buy", "limit", 0.1, price=51000.0)
        resp = await exchange.place_order(req)
        assert resp.status == "filled"

        # 限价高于当前价 (买入) -> pending
        req2 = OrderRequest("BTC/USDT", "buy", "limit", 0.1, price=49000.0)
        resp2 = await exchange.place_order(req2)
        assert resp2.status == "pending"
        print(f"✅ 限价单: 成交={resp.status}, 未成交={resp2.status}")

    @pytest.mark.asyncio
    async def test_pnl_tracking(self):
        """测试完整盈亏追踪"""
        exchange = PaperExchange(initial_capital=100000, commission_rate=0.001, slippage_rate=0)

        exchange.set_price("ETH/USDT", 2000.0)
        await exchange.place_order(OrderRequest("ETH/USDT", "buy", "market", 10.0))

        # 涨 10%
        exchange.set_price("ETH/USDT", 2200.0)
        await exchange.place_order(OrderRequest("ETH/USDT", "sell", "market", 10.0))

        account = await exchange.get_account()
        assert exchange.realized_pnl > 0
        assert account.total_equity > 100000  # 扣除手续费后仍盈利
        print(f"✅ PnL追踪: realized={exchange.realized_pnl:.2f}, equity={account.total_equity:.2f}")


# ──────── 测试风控管理 ────────

class TestRiskManager:

    @pytest.mark.asyncio
    async def test_daily_trade_limit(self):
        """测试日交易次数限制"""
        rm = RiskManager(max_daily_trades=3)
        account = AccountInfo(100000, 50000, 50000, 0, 0)

        for i in range(3):
            passed, _ = rm.check_order(
                OrderRequest("BTC/USDT", "buy", "market", 0.01),
                account
            )
            assert passed

        passed, reason = rm.check_order(
            OrderRequest("BTC/USDT", "buy", "market", 0.01),
            account
        )
        assert not passed
        assert "limit" in reason.lower()
        print(f"✅ 日交易限制: 第4次被拒绝 ({reason})")


# 需要导入AccountInfo
from app.execution.base import AccountInfo


# ──────── 测试执行管理器 ────────

class TestExecutionManager:

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整交易流程: 创建交易所 -> 启动策略 -> 执行信号 -> 查看组合"""
        manager = ExecutionManager()
        paper = manager.create_paper_exchange("paper", 100000)
        paper.set_price("BTC/USDT", 50000.0)

        # 启动策略
        strat = StrategyRegistry.create("DualMAStrategy")
        manager.start_strategy(1, "paper", strat)

        actives = manager.get_active_strategies()
        assert 1 in actives
        assert actives[1]["running"] is True
        print(f"✅ 策略启动: {actives[1]['strategy_name']}")

        # 执行买入信号
        resp = await manager.execute_signal("paper", "BTC/USDT", 1, 0.5, strategy_id=1)
        assert resp.status == "filled"
        print(f"✅ 买入执行: {resp.filled_quantity} BTC @ {resp.filled_price:.2f}")

        # 查看组合
        portfolio = await manager.get_portfolio_summary("paper")
        assert portfolio["total_equity"] > 0
        assert len(portfolio["positions"]) == 1
        print(f"✅ 组合: equity={portfolio['total_equity']:.2f}, "
              f"positions={len(portfolio['positions'])}")

        # 涨价后卖出
        paper.set_price("BTC/USDT", 55000.0)
        resp = await manager.execute_signal("paper", "BTC/USDT", -1, 0.5, strategy_id=1)
        assert resp.status == "filled"

        portfolio = await manager.get_portfolio_summary("paper")
        assert len(portfolio["positions"]) == 0
        assert portfolio["realized_pnl"] > 0
        print(f"✅ 卖出后: pnl={portfolio['realized_pnl']:.2f}")

        # 停止策略
        manager.stop_strategy(1)
        assert manager.active_strategies[1]["running"] is False
        print("✅ 策略停止")

        await manager.close_all()

    @pytest.mark.asyncio
    async def test_multiple_exchanges(self):
        """测试多交易所管理"""
        manager = ExecutionManager()
        paper1 = manager.create_paper_exchange("paper_crypto", 50000)
        paper2 = manager.create_paper_exchange("paper_stock", 100000)

        paper1.set_price("BTC/USDT", 50000)
        paper2.set_price("AAPL", 200)

        await manager.execute_signal("paper_crypto", "BTC/USDT", 1, 0.5)
        await manager.execute_signal("paper_stock", "AAPL", 1, 100)

        p1 = await manager.get_portfolio_summary("paper_crypto")
        p2 = await manager.get_portfolio_summary("paper_stock")

        assert len(p1["positions"]) == 1
        assert len(p2["positions"]) == 1
        print(f"✅ 多交易所: crypto={p1['positions'][0]['symbol']}, stock={p2['positions'][0]['symbol']}")

        await manager.close_all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-p", "no:warnings", "-s"])
