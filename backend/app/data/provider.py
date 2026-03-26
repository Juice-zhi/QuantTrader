"""
统一数据提供接口 - 供因子计算、回测、策略调用

这是整个系统的"数据层入口": 所有模块通过 DataProvider 获取数据,
不直接操作数据库。这样做的好处是:
1. 统一的缓存机制
2. 统一的数据格式
3. 易于切换数据源
"""
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Symbol, OHLCV, TimeFrame, MarketType
from app.data.fetcher import UnifiedFetcher
from app.data.storage import DataStorage


class DataProvider:
    """
    统一数据接口

    用法:
        provider = DataProvider(session)
        df = await provider.get_ohlcv("BTC/USDT", "1d", exchange="binance")
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.storage = DataStorage(session)
        self.fetcher = UnifiedFetcher()

    async def get_ohlcv(
        self,
        symbol_name: str,
        timeframe: str = "1d",
        exchange: str = "binance",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        auto_fetch: bool = True,
    ) -> pd.DataFrame:
        """
        获取K线数据 - 优先从数据库读取, 不足时自动抓取

        Args:
            symbol_name: 标的名称
            timeframe: 时间粒度
            exchange: 交易所
            start_date: 起始时间
            end_date: 结束时间
            auto_fetch: 数据不足时是否自动从网络抓取

        Returns:
            DataFrame [timestamp, open, high, low, close, volume]
        """
        # 1. 尝试从数据库读取
        market_type = self._detect_market_type(symbol_name, exchange)
        symbol = await self.storage.get_or_create_symbol(
            symbol_name, market_type, exchange
        )

        df = await self._query_ohlcv(symbol.id, timeframe, start_date, end_date)

        # 2. 如果数据不足, 从网络抓取并存储
        if auto_fetch and (df.empty or (start_date and not df.empty and df["timestamp"].min() > start_date)):
            fetch_since = start_date
            if not df.empty:
                # 增量抓取: 从数据库最新时间之后开始
                latest = await self.storage.get_latest_timestamp(symbol.id, timeframe)
                if latest and (not fetch_since or latest > fetch_since):
                    fetch_since = latest

            fetched_df = await self.fetcher.fetch_ohlcv(
                symbol_name, timeframe, exchange, since=fetch_since
            )
            if not fetched_df.empty:
                await self.storage.store_ohlcv(symbol.id, timeframe, fetched_df)
                await self.session.commit()
                # 重新查询完整数据
                df = await self._query_ohlcv(symbol.id, timeframe, start_date, end_date)

        return df

    async def _query_ohlcv(
        self,
        symbol_id: int,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """从数据库查询K线数据"""
        tf = TimeFrame(timeframe)
        conditions = [
            OHLCV.symbol_id == symbol_id,
            OHLCV.timeframe == tf,
        ]
        if start_date:
            conditions.append(OHLCV.timestamp >= start_date)
        if end_date:
            conditions.append(OHLCV.timestamp <= end_date)

        result = await self.session.execute(
            select(
                OHLCV.timestamp,
                OHLCV.open, OHLCV.high, OHLCV.low, OHLCV.close, OHLCV.volume
            )
            .where(and_(*conditions))
            .order_by(OHLCV.timestamp)
        )
        rows = result.all()

        if not rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        return df

    async def get_symbols(self, market_type: Optional[str] = None) -> list[dict]:
        """获取所有交易标的"""
        query = select(Symbol)
        if market_type:
            query = query.where(Symbol.market_type == MarketType(market_type))
        result = await self.session.execute(query)
        symbols = result.scalars().all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "market_type": s.market_type.value,
                "exchange": s.exchange,
                "is_active": s.is_active,
            }
            for s in symbols
        ]

    @staticmethod
    def _detect_market_type(symbol_name: str, exchange: str) -> MarketType:
        """自动检测市场类型"""
        if "/" in symbol_name:
            return MarketType.CRYPTO
        if exchange in ("binance", "okx", "bybit"):
            return MarketType.CRYPTO
        if symbol_name.endswith(".HK"):
            return MarketType.HK_STOCK
        if symbol_name.endswith((".SS", ".SZ")):
            return MarketType.CN_STOCK
        return MarketType.US_STOCK

    async def close(self):
        await self.fetcher.close()
