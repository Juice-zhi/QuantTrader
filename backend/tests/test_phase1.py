"""
Phase 1 测试: 数据库模型 + 数据存储 + 数据提供
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 使用测试数据库
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_quanttrader.db"

from app.database.engine import engine, AsyncSessionLocal, init_db, Base
from app.database.models import (
    Symbol, OHLCV, MarketType, TimeFrame, FactorMeta, FactorValue,
    Strategy, StrategyStatus, BacktestResult, Order, OrderSide,
    OrderType, OrderStatus, ExecutionMode, Trade, Position, PortfolioSnapshot
)
from app.data.storage import DataStorage
from app.data.provider import DataProvider


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def setup_db():
    """创建测试数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(setup_db):
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


# ──────── 测试数据库模型创建 ────────

class TestDatabaseModels:
    """测试所有数据库表是否能正常创建和操作"""

    @pytest.mark.asyncio
    async def test_create_symbol(self, session):
        """测试创建交易标的"""
        symbol = Symbol(
            name="BTC/USDT",
            market_type=MarketType.CRYPTO,
            exchange="binance",
            base_currency="BTC",
            quote_currency="USDT",
        )
        session.add(symbol)
        await session.flush()

        assert symbol.id is not None
        assert symbol.name == "BTC/USDT"
        assert symbol.market_type == MarketType.CRYPTO
        assert symbol.is_active is True
        print(f"✅ Symbol 创建成功: {symbol.name} (id={symbol.id})")

    @pytest.mark.asyncio
    async def test_create_ohlcv(self, session):
        """测试创建K线数据"""
        symbol = Symbol(
            name="ETH/USDT",
            market_type=MarketType.CRYPTO,
            exchange="binance",
            base_currency="ETH",
            quote_currency="USDT",
        )
        session.add(symbol)
        await session.flush()

        ohlcv = OHLCV(
            symbol_id=symbol.id,
            timeframe=TimeFrame.D1,
            timestamp=datetime(2024, 1, 1),
            open=2000.0,
            high=2100.0,
            low=1950.0,
            close=2050.0,
            volume=1000000.0,
        )
        session.add(ohlcv)
        await session.flush()

        assert ohlcv.id is not None
        assert ohlcv.close == 2050.0
        print(f"✅ OHLCV 创建成功: {symbol.name} @ {ohlcv.timestamp}")

    @pytest.mark.asyncio
    async def test_create_strategy(self, session):
        """测试创建策略"""
        strategy = Strategy(
            name="BTC布林带均值回归",
            strategy_type="MeanReversionStrategy",
            description="基于布林带的均值回归策略",
            params={"window": 20, "num_std": 2, "stop_loss": 0.05},
            status=StrategyStatus.INACTIVE,
        )
        session.add(strategy)
        await session.flush()

        assert strategy.id is not None
        assert strategy.params["window"] == 20
        print(f"✅ Strategy 创建成功: {strategy.name}")

    @pytest.mark.asyncio
    async def test_create_order_and_trade(self, session):
        """测试创建订单和成交记录"""
        strategy = Strategy(
            name="Test Strategy",
            strategy_type="TestStrategy",
            params={},
        )
        session.add(strategy)
        await session.flush()

        order = Order(
            strategy_id=strategy.id,
            symbol_name="BTC/USDT",
            exchange="binance",
            execution_mode=ExecutionMode.PAPER,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            status=OrderStatus.FILLED,
            filled_price=50000.0,
            filled_quantity=0.1,
            fee=5.0,
        )
        session.add(order)
        await session.flush()

        trade = Trade(
            order_id=order.id,
            symbol_name="BTC/USDT",
            side=OrderSide.BUY,
            price=50000.0,
            quantity=0.1,
            fee=5.0,
        )
        session.add(trade)
        await session.flush()

        assert order.id is not None
        assert trade.id is not None
        print(f"✅ Order + Trade 创建成功: {order.symbol_name} {order.side.value} @ {order.filled_price}")

    @pytest.mark.asyncio
    async def test_create_backtest_result(self, session):
        """测试创建回测结果"""
        strategy = Strategy(name="BT Test", strategy_type="Test", params={})
        session.add(strategy)
        await session.flush()

        bt = BacktestResult(
            strategy_id=strategy.id,
            symbol_name="BTC/USDT",
            timeframe=TimeFrame.D1,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=100000.0,
            final_capital=125000.0,
            total_return=0.25,
            annual_return=0.25,
            sharpe_ratio=1.8,
            max_drawdown=0.12,
            win_rate=0.62,
            profit_factor=2.1,
            total_trades=48,
            equity_curve=[{"date": "2024-01-01", "equity": 100000}],
        )
        session.add(bt)
        await session.flush()

        assert bt.id is not None
        assert bt.win_rate == 0.62
        print(f"✅ BacktestResult 创建成功: 胜率={bt.win_rate}, 夏普={bt.sharpe_ratio}")


# ──────── 测试数据存储层 ────────

class TestDataStorage:
    """测试数据入库"""

    @pytest.mark.asyncio
    async def test_store_ohlcv(self, session):
        """测试 DataFrame 数据入库"""
        storage = DataStorage(session)

        symbol = await storage.get_or_create_symbol(
            "AAPL", MarketType.US_STOCK, "nasdaq", "AAPL", "USD"
        )

        # 构造测试数据
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "open": [150.0 + i for i in range(10)],
            "high": [155.0 + i for i in range(10)],
            "low": [148.0 + i for i in range(10)],
            "close": [152.0 + i for i in range(10)],
            "volume": [1000000 + i * 10000 for i in range(10)],
        })

        count = await storage.store_ohlcv(symbol.id, "1d", df)
        assert count == 10
        print(f"✅ DataStorage.store_ohlcv 成功: 存入 {count} 条")

        # 测试重复存储不会重复
        count2 = await storage.store_ohlcv(symbol.id, "1d", df)
        assert count2 == 0
        print(f"✅ 重复数据检测: 重复存入 {count2} 条 (符合预期)")

    @pytest.mark.asyncio
    async def test_get_latest_timestamp(self, session):
        """测试获取最新时间戳"""
        storage = DataStorage(session)
        symbol = await storage.get_or_create_symbol(
            "MSFT", MarketType.US_STOCK, "nasdaq"
        )

        dates = pd.date_range("2024-06-01", periods=5, freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "open": [400.0] * 5,
            "high": [410.0] * 5,
            "low": [395.0] * 5,
            "close": [405.0] * 5,
            "volume": [500000] * 5,
        })
        await storage.store_ohlcv(symbol.id, "1d", df)

        latest = await storage.get_latest_timestamp(symbol.id, "1d")
        assert latest == dates[-1].to_pydatetime()
        print(f"✅ 最新时间戳: {latest}")


# ──────── 测试数据提供层 ────────

class TestDataProvider:
    """测试统一数据接口"""

    @pytest.mark.asyncio
    async def test_get_ohlcv_from_db(self, session):
        """测试从数据库获取数据"""
        # 先存一些数据
        storage = DataStorage(session)
        symbol = await storage.get_or_create_symbol(
            "GOOG", MarketType.US_STOCK, "nasdaq"
        )
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "open": [140.0 + i * 0.5 for i in range(20)],
            "high": [142.0 + i * 0.5 for i in range(20)],
            "low": [138.0 + i * 0.5 for i in range(20)],
            "close": [141.0 + i * 0.5 for i in range(20)],
            "volume": [2000000] * 20,
        })
        await storage.store_ohlcv(symbol.id, "1d", df)
        await session.commit()

        # 使用 DataProvider 查询
        provider = DataProvider(session)
        result = await provider.get_ohlcv(
            "GOOG", "1d", exchange="nasdaq", auto_fetch=False
        )

        assert len(result) == 20
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert result.iloc[0]["close"] == 141.0
        print(f"✅ DataProvider.get_ohlcv 成功: 获取 {len(result)} 条数据")

    @pytest.mark.asyncio
    async def test_market_type_detection(self, session):
        """测试市场类型自动检测"""
        provider = DataProvider(session)

        assert provider._detect_market_type("BTC/USDT", "binance") == MarketType.CRYPTO
        assert provider._detect_market_type("AAPL", "nasdaq") == MarketType.US_STOCK
        assert provider._detect_market_type("0700.HK", "hkex") == MarketType.HK_STOCK
        assert provider._detect_market_type("600519.SS", "sse") == MarketType.CN_STOCK
        print("✅ 市场类型检测正确")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-p", "no:warnings"])
