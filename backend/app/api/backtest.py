"""
回测 API
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
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
    # 获取数据
    provider = DataProvider(session)
    try:
        start = datetime.fromisoformat(req.start_date) if req.start_date else None
        end = datetime.fromisoformat(req.end_date) if req.end_date else None
        df = await provider.get_ohlcv(req.symbol, req.timeframe, req.exchange, start, end)

        if df.empty:
            return {"error": "No data available for backtest"}

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

        # 保存到数据库
        bt = BacktestResult(
            strategy_id=None,
            symbol_name=req.symbol,
            timeframe=TimeFrame(req.timeframe),
            start_date=start or df["timestamp"].iloc[0],
            end_date=end or df["timestamp"].iloc[-1],
            initial_capital=req.initial_capital,
            final_capital=result["equity_curve"][-1]["equity"],
            total_return=result["metrics"]["total_return"],
            annual_return=result["metrics"]["annual_return"],
            sharpe_ratio=result["metrics"]["sharpe_ratio"],
            max_drawdown=result["metrics"]["max_drawdown"],
            win_rate=result["metrics"]["win_rate"],
            profit_factor=result["metrics"]["profit_factor"],
            total_trades=result["metrics"]["total_trades"],
            equity_curve=result["equity_curve"],
            trade_log=result["trades"],
            params_used=req.params,
        )
        session.add(bt)
        await session.flush()

        return {
            "backtest_id": bt.id,
            "strategy": strategy.info(),
            "metrics": result["metrics"],
            "equity_curve": result["equity_curve"],
            "trades": result["trades"],
            "data_points": len(df),
        }
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
