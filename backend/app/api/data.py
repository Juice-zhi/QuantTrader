"""
数据 API - K线数据查询和抓取
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import get_session
from app.data.provider import DataProvider

router = APIRouter(prefix="/api/data", tags=["Data"])


@router.get("/ohlcv")
async def get_ohlcv(
    symbol: str = Query(..., description="标的, e.g. BTC/USDT, AAPL"),
    timeframe: str = Query("1d"),
    exchange: str = Query("binance"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None),
    auto_fetch: bool = Query(True, description="数据不足时自动从网络抓取"),
    session: AsyncSession = Depends(get_session),
):
    """获取K线数据"""
    provider = DataProvider(session)
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    try:
        df = await provider.get_ohlcv(symbol, timeframe, exchange, start, end, auto_fetch)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(df),
            "data": df.to_dict(orient="records"),
        }
    finally:
        await provider.close()


@router.get("/symbols")
async def get_symbols(
    market_type: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """获取所有交易标的"""
    provider = DataProvider(session)
    symbols = await provider.get_symbols(market_type)
    return {"symbols": symbols, "count": len(symbols)}
