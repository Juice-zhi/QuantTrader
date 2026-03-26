"""
数据存储层 - 将抓取的数据存入数据库
"""
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database.models import Symbol, OHLCV, MarketType, TimeFrame


class DataStorage:
    """数据入库服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_symbol(
        self,
        name: str,
        market_type: MarketType,
        exchange: str,
        base_currency: str = "",
        quote_currency: str = "",
    ) -> Symbol:
        """获取或创建交易标的"""
        result = await self.session.execute(
            select(Symbol).where(
                and_(Symbol.name == name, Symbol.exchange == exchange)
            )
        )
        symbol = result.scalar_one_or_none()

        if symbol is None:
            symbol = Symbol(
                name=name,
                market_type=market_type,
                exchange=exchange,
                base_currency=base_currency or name.split("/")[0] if "/" in name else name,
                quote_currency=quote_currency or name.split("/")[1] if "/" in name else "USD",
            )
            self.session.add(symbol)
            await self.session.flush()

        return symbol

    async def store_ohlcv(
        self,
        symbol_id: int,
        timeframe: str,
        df: pd.DataFrame,
    ) -> int:
        """
        将 DataFrame 存入 ohlcv 表

        Args:
            symbol_id: 标的ID
            timeframe: 时间粒度
            df: DataFrame with columns [timestamp, open, high, low, close, volume]

        Returns:
            插入的行数
        """
        if df.empty:
            return 0

        tf = TimeFrame(timeframe)
        count = 0

        for _, row in df.iterrows():
            # 检查是否已存在
            exists = await self.session.execute(
                select(OHLCV.id).where(
                    and_(
                        OHLCV.symbol_id == symbol_id,
                        OHLCV.timeframe == tf,
                        OHLCV.timestamp == row["timestamp"],
                    )
                )
            )
            if exists.scalar_one_or_none() is not None:
                continue

            ohlcv = OHLCV(
                symbol_id=symbol_id,
                timeframe=tf,
                timestamp=row["timestamp"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            self.session.add(ohlcv)
            count += 1

        await self.session.flush()
        return count

    async def get_latest_timestamp(
        self, symbol_id: int, timeframe: str
    ) -> Optional[datetime]:
        """获取某标的某时间粒度的最新数据时间 (增量抓取用)"""
        result = await self.session.execute(
            select(OHLCV.timestamp)
            .where(
                and_(
                    OHLCV.symbol_id == symbol_id,
                    OHLCV.timeframe == TimeFrame(timeframe),
                )
            )
            .order_by(OHLCV.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
