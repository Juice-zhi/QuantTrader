"""
因子 API - 因子库查询, 计算, 分析
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import get_session
from app.data.provider import DataProvider
from app.factors.registry import FactorRegistry
from app.factors.composite import FactorAnalyzer

# 触发因子注册
from app.factors import technical, momentum, volatility, volume, composite

router = APIRouter(prefix="/api/factors", tags=["Factors"])


@router.get("/list")
async def list_factors(category: Optional[str] = Query(None)):
    """列出所有因子"""
    if category:
        factors = FactorRegistry.list_by_category(category)
    else:
        factors = FactorRegistry.list_all()
    return {"factors": factors, "count": len(factors), "categories": FactorRegistry.categories()}


@router.get("/categories")
async def get_categories():
    """获取所有因子分类"""
    return {"categories": FactorRegistry.categories()}


class FactorComputeRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    exchange: str = "binance"
    factor_name: str
    params: dict = {}
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/compute")
async def compute_factor(
    req: FactorComputeRequest,
    session: AsyncSession = Depends(get_session),
):
    """计算因子值"""
    provider = DataProvider(session)
    try:
        start = datetime.fromisoformat(req.start_date) if req.start_date else None
        end = datetime.fromisoformat(req.end_date) if req.end_date else None
        df = await provider.get_ohlcv(req.symbol, req.timeframe, req.exchange, start, end)

        if df.empty:
            return {"error": "No data available"}

        factor = FactorRegistry.create(req.factor_name, **req.params)
        values = factor.compute_with_validation(df)

        result = df[["timestamp"]].copy()
        result["value"] = values
        result = result.dropna()

        return {
            "factor": factor.info(),
            "symbol": req.symbol,
            "count": len(result),
            "data": [
                {"timestamp": str(row["timestamp"]), "value": round(row["value"], 6)}
                for _, row in result.iterrows()
            ],
        }
    finally:
        await provider.close()


class FactorICRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    exchange: str = "binance"
    factor_name: str
    params: dict = {}
    forward_period: int = 5


@router.post("/ic")
async def compute_factor_ic(
    req: FactorICRequest,
    session: AsyncSession = Depends(get_session),
):
    """计算因子IC值"""
    provider = DataProvider(session)
    try:
        df = await provider.get_ohlcv(req.symbol, req.timeframe, req.exchange)
        if df.empty:
            return {"error": "No data available"}

        factor = FactorRegistry.create(req.factor_name, **req.params)
        values = factor.compute_with_validation(df)
        forward_returns = df["close"].pct_change(req.forward_period).shift(-req.forward_period)

        ic = FactorAnalyzer.compute_ic(values, forward_returns)
        stats = FactorAnalyzer.compute_factor_stats(values)

        return {
            "factor": factor.info(),
            "ic": round(ic, 6),
            "forward_period": req.forward_period,
            "stats": stats,
        }
    finally:
        await provider.close()
