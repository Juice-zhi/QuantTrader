"""
交易所基类 - 所有交易所连接器必须实现此接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


@dataclass
class OrderRequest:
    """下单请求"""
    symbol: str
    side: str          # "buy" / "sell"
    order_type: str    # "market" / "limit"
    quantity: float
    price: Optional[float] = None   # 限价单才需要
    stop_price: Optional[float] = None
    strategy_id: Optional[int] = None


@dataclass
class OrderResponse:
    """下单响应"""
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: str        # "submitted" / "filled" / "rejected"
    filled_price: Optional[float] = None
    filled_quantity: Optional[float] = None
    fee: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str = ""


@dataclass
class PositionInfo:
    """持仓信息"""
    symbol: str
    side: str          # "long" / "short"
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0


@dataclass
class AccountInfo:
    """账户信息"""
    total_equity: float
    available_cash: float
    positions_value: float
    unrealized_pnl: float
    realized_pnl: float


class BaseExchange(ABC):
    """
    交易所基类

    所有交易所(包括模拟)实现相同接口:
    - place_order: 下单
    - cancel_order: 撤单
    - get_positions: 获取持仓
    - get_account: 获取账户信息
    - get_ticker: 获取最新价格
    """

    name: str = ""
    is_paper: bool = False

    @abstractmethod
    async def place_order(self, request: OrderRequest) -> OrderResponse:
        raise NotImplementedError

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_positions(self) -> list[PositionInfo]:
        raise NotImplementedError

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        raise NotImplementedError

    @abstractmethod
    async def get_ticker(self, symbol: str) -> dict:
        """返回 {"bid": ..., "ask": ..., "last": ..., "volume": ...}"""
        raise NotImplementedError

    async def close(self):
        """关闭连接"""
        pass
