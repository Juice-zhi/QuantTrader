"""
CCXT 交易所连接器 - 支持 Binance, OKX, Bybit 等

通过 ccxt 统一接口封装, 实现 BaseExchange 接口
"""
from typing import Optional

import ccxt.async_support as ccxt_async

from app.execution.base import (
    BaseExchange, OrderRequest, OrderResponse, PositionInfo, AccountInfo
)
from app.config import settings


class CCXTExchange(BaseExchange):
    """
    CCXT 统一交易所连接器

    支持所有 ccxt 支持的交易所, 常用:
    - binance
    - okx
    - bybit
    """

    is_paper = False

    EXCHANGE_CONFIGS = {
        "binance": {
            "class": ccxt_async.binance,
            "api_key_setting": "BINANCE_API_KEY",
            "secret_setting": "BINANCE_SECRET",
        },
        "okx": {
            "class": ccxt_async.okx,
            "api_key_setting": "OKX_API_KEY",
            "secret_setting": "OKX_SECRET",
        },
        "bybit": {
            "class": ccxt_async.bybit,
            "api_key_setting": "BYBIT_API_KEY",
            "secret_setting": "BYBIT_SECRET",
        },
    }

    def __init__(self, exchange_name: str = "binance", sandbox: bool = False):
        self.name = exchange_name
        self._exchange: Optional[ccxt_async.Exchange] = None
        self._sandbox = sandbox

    async def _get_exchange(self) -> ccxt_async.Exchange:
        if self._exchange is None:
            config = self.EXCHANGE_CONFIGS.get(self.name)
            if config is None:
                raise ValueError(f"Unsupported exchange: {self.name}")

            api_key = getattr(settings, config["api_key_setting"], "")
            secret = getattr(settings, config["secret_setting"], "")

            exchange_config = {
                "apiKey": api_key,
                "secret": secret,
                "enableRateLimit": True,
            }
            if self.name == "okx" and settings.OKX_PASSPHRASE:
                exchange_config["password"] = settings.OKX_PASSPHRASE

            self._exchange = config["class"](exchange_config)

            if self._sandbox:
                self._exchange.set_sandbox_mode(True)

        return self._exchange

    async def place_order(self, request: OrderRequest) -> OrderResponse:
        exchange = await self._get_exchange()
        try:
            if request.order_type == "market":
                order = await exchange.create_order(
                    request.symbol, "market", request.side, request.quantity
                )
            elif request.order_type == "limit":
                order = await exchange.create_order(
                    request.symbol, "limit", request.side, request.quantity, request.price
                )
            else:
                order = await exchange.create_order(
                    request.symbol, request.order_type, request.side,
                    request.quantity, request.price
                )

            return OrderResponse(
                order_id=str(order.get("id", "")),
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                price=order.get("price"),
                status=order.get("status", "submitted"),
                filled_price=order.get("average"),
                filled_quantity=order.get("filled"),
                fee=order.get("fee", {}).get("cost", 0) if order.get("fee") else 0,
            )
        except Exception as e:
            return OrderResponse(
                order_id="",
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                price=request.price,
                status="rejected",
                message=str(e),
            )

    async def cancel_order(self, order_id: str) -> bool:
        exchange = await self._get_exchange()
        try:
            await exchange.cancel_order(order_id)
            return True
        except Exception:
            return False

    async def get_positions(self) -> list[PositionInfo]:
        exchange = await self._get_exchange()
        try:
            balance = await exchange.fetch_balance()
            positions = []
            for currency, info in balance.get("total", {}).items():
                if info and float(info) > 0 and currency not in ("USDT", "USD", "BUSD"):
                    positions.append(PositionInfo(
                        symbol=f"{currency}/USDT",
                        side="long",
                        quantity=float(info),
                        entry_price=0,
                        current_price=0,
                        unrealized_pnl=0,
                    ))
            return positions
        except Exception:
            return []

    async def get_account(self) -> AccountInfo:
        exchange = await self._get_exchange()
        try:
            balance = await exchange.fetch_balance()
            free = float(balance.get("free", {}).get("USDT", 0) or 0)
            total = float(balance.get("total", {}).get("USDT", 0) or 0)
            return AccountInfo(
                total_equity=total,
                available_cash=free,
                positions_value=total - free,
                unrealized_pnl=0,
                realized_pnl=0,
            )
        except Exception as e:
            return AccountInfo(0, 0, 0, 0, 0)

    async def get_ticker(self, symbol: str) -> dict:
        exchange = await self._get_exchange()
        try:
            ticker = await exchange.fetch_ticker(symbol)
            return {
                "bid": ticker.get("bid", 0),
                "ask": ticker.get("ask", 0),
                "last": ticker.get("last", 0),
                "volume": ticker.get("quoteVolume", 0),
            }
        except Exception:
            return {"bid": 0, "ask": 0, "last": 0, "volume": 0}

    async def close(self):
        if self._exchange:
            await self._exchange.close()
            self._exchange = None
