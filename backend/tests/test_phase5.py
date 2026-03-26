"""
Phase 5 测试: FastAPI REST API
"""
import sys
import os
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_api.db"

from app.main import app
from app.database.engine import init_db, engine, Base


@pytest.fixture(scope="module")
async def client():
    # 确保表已创建
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestRootAndHealth:

    @pytest.mark.asyncio
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "QuantTrader"
        print(f"✅ Root: {data['name']} v{data['version']}")

    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        print("✅ Health check OK")


class TestFactorsAPI:

    @pytest.mark.asyncio
    async def test_list_factors(self, client):
        resp = await client.get("/api/factors/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 25
        print(f"✅ Factors: {data['count']} factors, categories={data['categories']}")

    @pytest.mark.asyncio
    async def test_list_by_category(self, client):
        resp = await client.get("/api/factors/list?category=technical")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 9
        print(f"✅ Technical factors: {data['count']}")

    @pytest.mark.asyncio
    async def test_categories(self, client):
        resp = await client.get("/api/factors/categories")
        assert resp.status_code == 200
        cats = resp.json()["categories"]
        assert "technical" in cats
        print(f"✅ Categories: {cats}")


class TestStrategiesAPI:

    @pytest.mark.asyncio
    async def test_list_strategy_types(self, client):
        resp = await client.get("/api/strategies/types")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["strategies"]) >= 5
        print(f"✅ Strategy types: {len(data['strategies'])}")

    @pytest.mark.asyncio
    async def test_create_strategy(self, client):
        resp = await client.post("/api/strategies/", json={
            "name": "Test Dual MA",
            "strategy_type": "DualMAStrategy",
            "params": {"fast_period": 10, "slow_period": 30},
            "exchange": "paper",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        print(f"✅ Created strategy id={data['id']}")

    @pytest.mark.asyncio
    async def test_list_strategies(self, client):
        resp = await client.get("/api/strategies/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["strategies"]) >= 1
        print(f"✅ Listed {len(data['strategies'])} strategies")


class TestTradingAPI:

    @pytest.mark.asyncio
    async def test_list_exchanges(self, client):
        resp = await client.get("/api/trading/exchanges")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["exchanges"]) >= 1
        print(f"✅ Exchanges: {[e['name'] for e in data['exchanges']]}")

    @pytest.mark.asyncio
    async def test_set_price_and_execute(self, client):
        # 设置价格
        resp = await client.post("/api/trading/set-price", json={
            "symbol": "BTC/USDT", "price": 50000.0, "exchange": "paper"
        })
        assert resp.status_code == 200

        # 执行买入
        resp = await client.post("/api/trading/execute", json={
            "exchange": "paper", "symbol": "BTC/USDT",
            "signal": 1, "quantity": 0.5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "filled"
        print(f"✅ Executed: {data['status']} @ {data['filled_price']:.2f}")

    @pytest.mark.asyncio
    async def test_portfolio(self, client):
        resp = await client.get("/api/trading/portfolio?exchange=paper")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_equity"] > 0
        print(f"✅ Portfolio: equity={data['total_equity']:.2f}, "
              f"positions={len(data['positions'])}")


class TestDataAPI:

    @pytest.mark.asyncio
    async def test_get_symbols(self, client):
        resp = await client.get("/api/data/symbols")
        assert resp.status_code == 200
        print(f"✅ Symbols: {resp.json()['count']}")


class TestBacktestAPI:

    @pytest.mark.asyncio
    async def test_list_results(self, client):
        resp = await client.get("/api/backtest/results")
        assert resp.status_code == 200
        print(f"✅ Backtest results: {len(resp.json()['results'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-p", "no:warnings", "-s"])
