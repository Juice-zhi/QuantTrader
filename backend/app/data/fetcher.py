"""
多源数据抓取 - 统一接口获取加密货币和股票历史数据

支持数据源:
- ccxt: 加密货币 (Binance, OKX, Bybit 等)
- yfinance: 美股, 港股
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import ccxt.async_support as ccxt_async
import pandas as pd
import yfinance as yf

from app.config import settings


# ccxt timeframe -> 我们的 TimeFrame 映射
TIMEFRAME_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w",
}

# yfinance interval 映射
YF_INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "1h", "1d": "1d", "1w": "1wk",
}


class CryptoFetcher:
    """加密货币数据抓取 (基于 ccxt)"""

    EXCHANGE_CLASSES = {
        "binance": ccxt_async.binance,
        "okx": ccxt_async.okx,
        "bybit": ccxt_async.bybit,
    }

    def __init__(self, exchange_name: str = "binance"):
        self.exchange_name = exchange_name
        self._exchange: Optional[ccxt_async.Exchange] = None

    async def _get_exchange(self) -> ccxt_async.Exchange:
        if self._exchange is None:
            cls = self.EXCHANGE_CLASSES.get(self.exchange_name)
            if cls is None:
                raise ValueError(f"Unsupported exchange: {self.exchange_name}")
            config = {"enableRateLimit": True}
            # 添加 API keys (如果有)
            if self.exchange_name == "binance" and settings.BINANCE_API_KEY:
                config["apiKey"] = settings.BINANCE_API_KEY
                config["secret"] = settings.BINANCE_SECRET
            elif self.exchange_name == "okx" and settings.OKX_API_KEY:
                config["apiKey"] = settings.OKX_API_KEY
                config["secret"] = settings.OKX_SECRET
                config["password"] = settings.OKX_PASSPHRASE
            self._exchange = cls(config)
        return self._exchange

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        抓取K线数据

        Args:
            symbol: 交易对, e.g. "BTC/USDT"
            timeframe: 时间粒度, e.g. "1d", "1h", "5m"
            since: 起始时间
            limit: 最大条数

        Returns:
            DataFrame with columns: [timestamp, open, high, low, close, volume]
        """
        exchange = await self._get_exchange()
        since_ms = int(since.timestamp() * 1000) if since else None

        all_data = []
        fetched = 0
        current_since = since_ms

        while fetched < limit:
            batch_limit = min(1000, limit - fetched)
            try:
                ohlcv = await exchange.fetch_ohlcv(
                    symbol, timeframe, since=current_since, limit=batch_limit
                )
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                break

            if not ohlcv:
                break

            all_data.extend(ohlcv)
            fetched += len(ohlcv)

            if len(ohlcv) < batch_limit:
                break

            # 下一批从最后一条的下一个时间开始
            current_since = ohlcv[-1][0] + 1

        if not all_data:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(all_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        return df

    async def fetch_symbols(self) -> list[str]:
        """获取交易所所有交易对"""
        exchange = await self._get_exchange()
        await exchange.load_markets()
        return list(exchange.symbols)

    async def close(self):
        if self._exchange:
            await self._exchange.close()
            self._exchange = None


class StockFetcher:
    """股票数据抓取 (基于 yfinance)"""

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y",
    ) -> pd.DataFrame:
        """
        抓取股票K线数据

        Args:
            symbol: 股票代码, e.g. "AAPL", "0700.HK"
            timeframe: 时间粒度
            start_date: 起始日期 "YYYY-MM-DD"
            end_date: 结束日期
            period: 时间范围 (当start_date为空时使用), e.g. "1y", "6mo", "max"
        """
        ticker = yf.Ticker(symbol)
        interval = YF_INTERVAL_MAP.get(timeframe, "1d")

        if start_date:
            hist = ticker.history(start=start_date, end=end_date, interval=interval)
        else:
            hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = hist.reset_index()
        # yfinance 返回的列名是大写的
        df = df.rename(columns={
            "Date": "timestamp", "Datetime": "timestamp",
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume"
        })
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        return df


class UnifiedFetcher:
    """统一数据抓取接口 - 自动识别市场类型"""

    def __init__(self):
        self._crypto_fetchers: dict[str, CryptoFetcher] = {}
        self._stock_fetcher = StockFetcher()

    def _get_crypto_fetcher(self, exchange: str = "binance") -> CryptoFetcher:
        if exchange not in self._crypto_fetchers:
            self._crypto_fetchers[exchange] = CryptoFetcher(exchange)
        return self._crypto_fetchers[exchange]

    @staticmethod
    def is_crypto(symbol: str) -> bool:
        """判断是否是加密货币 (包含 '/')"""
        return "/" in symbol

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        exchange: str = "binance",
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """统一抓取接口"""
        if self.is_crypto(symbol):
            fetcher = self._get_crypto_fetcher(exchange)
            return await fetcher.fetch_ohlcv(symbol, timeframe, since, limit)
        else:
            start_date = since.strftime("%Y-%m-%d") if since else None
            return self._stock_fetcher.fetch_ohlcv(symbol, timeframe, start_date=start_date)

    async def close(self):
        for fetcher in self._crypto_fetchers.values():
            await fetcher.close()
