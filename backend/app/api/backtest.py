"""
回测 API
"""
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import get_session
from app.database.models import BacktestResult, Strategy as StrategyModel, TimeFrame
from app.data.provider import DataProvider
from app.strategies.registry import StrategyRegistry
from app.backtest.engine import BacktestEngine, BacktestConfig

# 触发注册
from app.factors import technical, momentum, volatility, volume, composite
from app.strategies import mean_reversion, momentum_strategy, factor_combo, grid_trading, dual_ma, price_action, ict_strategy, trend_following, lgbm_strategy

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])

# ── 热门标的列表 ──

POPULAR_SYMBOLS = {
    "crypto": [
        {"symbol": "BTC/USDT", "name": "Bitcoin", "exchange": "binance"},
        {"symbol": "ETH/USDT", "name": "Ethereum", "exchange": "binance"},
        {"symbol": "SOL/USDT", "name": "Solana", "exchange": "binance"},
        {"symbol": "BNB/USDT", "name": "BNB", "exchange": "binance"},
        {"symbol": "XRP/USDT", "name": "Ripple", "exchange": "binance"},
        {"symbol": "DOGE/USDT", "name": "Dogecoin", "exchange": "binance"},
        {"symbol": "ADA/USDT", "name": "Cardano", "exchange": "binance"},
        {"symbol": "AVAX/USDT", "name": "Avalanche", "exchange": "binance"},
        {"symbol": "LINK/USDT", "name": "Chainlink", "exchange": "binance"},
        {"symbol": "DOT/USDT", "name": "Polkadot", "exchange": "binance"},
    ],
    "us_stock": [
        {"symbol": "AAPL", "name": "Apple", "exchange": "nasdaq"},
        {"symbol": "MSFT", "name": "Microsoft", "exchange": "nasdaq"},
        {"symbol": "GOOGL", "name": "Google", "exchange": "nasdaq"},
        {"symbol": "AMZN", "name": "Amazon", "exchange": "nasdaq"},
        {"symbol": "NVDA", "name": "NVIDIA", "exchange": "nasdaq"},
        {"symbol": "TSLA", "name": "Tesla", "exchange": "nasdaq"},
        {"symbol": "META", "name": "Meta", "exchange": "nasdaq"},
        {"symbol": "AMD", "name": "AMD", "exchange": "nasdaq"},
        {"symbol": "JPM", "name": "JPMorgan", "exchange": "nyse"},
        {"symbol": "V", "name": "Visa", "exchange": "nyse"},
        {"symbol": "SPY", "name": "S&P 500 ETF", "exchange": "nyse"},
        {"symbol": "QQQ", "name": "Nasdaq 100 ETF", "exchange": "nasdaq"},
    ],
    "hk_stock": [
        {"symbol": "0700.HK", "name": "腾讯控股", "exchange": "hkex"},
        {"symbol": "9988.HK", "name": "阿里巴巴", "exchange": "hkex"},
        {"symbol": "3690.HK", "name": "美团", "exchange": "hkex"},
        {"symbol": "9999.HK", "name": "网易", "exchange": "hkex"},
        {"symbol": "1810.HK", "name": "小米集团", "exchange": "hkex"},
        {"symbol": "2318.HK", "name": "中国平安", "exchange": "hkex"},
        {"symbol": "0005.HK", "name": "汇丰控股", "exchange": "hkex"},
        {"symbol": "9618.HK", "name": "京东集团", "exchange": "hkex"},
    ],
    "cn_stock": [
        {"symbol": "600519.SS", "name": "贵州茅台", "exchange": "sse"},
        {"symbol": "000858.SZ", "name": "五粮液", "exchange": "szse"},
        {"symbol": "601318.SS", "name": "中国平安", "exchange": "sse"},
        {"symbol": "000001.SZ", "name": "平安银行", "exchange": "szse"},
        {"symbol": "600036.SS", "name": "招商银行", "exchange": "sse"},
        {"symbol": "002594.SZ", "name": "比亚迪", "exchange": "szse"},
        {"symbol": "600900.SS", "name": "长江电力", "exchange": "sse"},
        {"symbol": "601012.SS", "name": "隆基绿能", "exchange": "sse"},
    ],
}


@router.get("/symbols")
async def get_popular_symbols():
    """获取热门交易标的列表, 按市场分类"""
    return POPULAR_SYMBOLS


def downsample_equity_curve(curve: list, max_points: int = 300) -> list:
    """将净值曲线降采样到 max_points 个点，保留首尾"""
    if len(curve) <= max_points:
        return curve
    step = len(curve) / max_points
    indices = [int(i * step) for i in range(max_points - 1)]
    indices.append(len(curve) - 1)  # 始终保留最后一个点
    return [curve[i] for i in indices]


class BacktestRequest(BaseModel):
    strategy_type: str
    params: dict = {}
    symbol: str
    timeframe: str = "1d"
    exchange: str = "binance"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    stop_loss: Optional[float] = None


@router.post("/run")
async def run_backtest(
    req: BacktestRequest,
    session: AsyncSession = Depends(get_session),
):
    """执行回测"""
    provider = DataProvider(session)
    try:
        start = datetime.fromisoformat(req.start_date) if req.start_date else None
        end = datetime.fromisoformat(req.end_date) if req.end_date else None
        df = await provider.get_ohlcv(req.symbol, req.timeframe, req.exchange, start, end)

        if df.empty:
            return JSONResponse(status_code=400, content={"error": f"No data for {req.symbol} on {req.exchange}"})

        if len(df) < 50:
            return JSONResponse(status_code=400, content={"error": f"Insufficient data: {len(df)} bars (need ≥50)"})

        # 创建策略
        strategy = StrategyRegistry.create(req.strategy_type, **req.params)

        # 执行回测
        config = BacktestConfig(
            initial_capital=req.initial_capital,
            commission_rate=req.commission_rate,
            slippage_rate=req.slippage_rate,
            stop_loss=req.stop_loss,
        )
        engine = BacktestEngine(config)
        result = engine.run(strategy, df)

        # 降采样净值曲线
        equity_curve_full = result["equity_curve"]
        equity_curve_sampled = downsample_equity_curve(equity_curve_full, max_points=300)

        # 保存到数据库
        bt = BacktestResult(
            strategy_id=None,
            symbol_name=req.symbol,
            timeframe=TimeFrame(req.timeframe),
            start_date=start or df["timestamp"].iloc[0],
            end_date=end or df["timestamp"].iloc[-1],
            initial_capital=req.initial_capital,
            final_capital=equity_curve_full[-1]["equity"],
            total_return=result["metrics"]["total_return"],
            annual_return=result["metrics"]["annual_return"],
            sharpe_ratio=result["metrics"]["sharpe_ratio"],
            max_drawdown=result["metrics"]["max_drawdown"],
            win_rate=result["metrics"]["win_rate"],
            profit_factor=result["metrics"]["profit_factor"],
            total_trades=result["metrics"]["total_trades"],
            equity_curve=equity_curve_sampled,  # 存降采样版本
            trade_log=result["trades"],
            params_used=req.params,
        )
        session.add(bt)
        await session.flush()

        return {
            "backtest_id": bt.id,
            "strategy": strategy.info(),
            "metrics": result["metrics"],
            "equity_curve": equity_curve_sampled,
            "trades": result["trades"],
            "data_points": len(df),
        }

    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Backtest failed: {str(e)[:300]}"})
    finally:
        await provider.close()


@router.get("/results")
async def list_backtest_results(
    session: AsyncSession = Depends(get_session),
):
    """列出所有回测结果"""
    result = await session.execute(
        select(BacktestResult).order_by(BacktestResult.id.desc()).limit(50)
    )
    results = result.scalars().all()
    return {
        "results": [
            {
                "id": r.id,
                "symbol": r.symbol_name,
                "timeframe": r.timeframe.value,
                "total_return": r.total_return,
                "sharpe_ratio": r.sharpe_ratio,
                "max_drawdown": r.max_drawdown,
                "win_rate": r.win_rate,
                "total_trades": r.total_trades,
                "created_at": str(r.created_at),
            }
            for r in results
        ]
    }


@router.get("/results/{backtest_id}")
async def get_backtest_result(
    backtest_id: int,
    session: AsyncSession = Depends(get_session),
):
    """获取回测详情"""
    result = await session.execute(
        select(BacktestResult).where(BacktestResult.id == backtest_id)
    )
    bt = result.scalar_one_or_none()
    if not bt:
        return {"error": "Backtest result not found"}

    return {
        "id": bt.id,
        "symbol": bt.symbol_name,
        "timeframe": bt.timeframe.value,
        "metrics": {
            "total_return": bt.total_return,
            "annual_return": bt.annual_return,
            "sharpe_ratio": bt.sharpe_ratio,
            "max_drawdown": bt.max_drawdown,
            "win_rate": bt.win_rate,
            "profit_factor": bt.profit_factor,
            "total_trades": bt.total_trades,
        },
        "equity_curve": bt.equity_curve,
        "trades": bt.trade_log,
        "params": bt.params_used,
    }
