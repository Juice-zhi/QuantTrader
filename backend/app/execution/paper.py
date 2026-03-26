"""
模拟交易引擎 (Paper Trading)

完整模拟:
- 市价单/限价单
- 手续费
- 滑点
- 持仓管理
- PnL计算
"""
import uuid
from datetime import datetime
from typing import Optional

from app.execution.base import (
    BaseExchange, OrderRequest, OrderResponse, PositionInfo, AccountInfo
)


class PaperExchange(BaseExchange):
    """
    模拟交易所

    完全在内存中运行, 模拟真实交易所的行为.
    通过 set_price() 注入最新价格来驱动模拟.
    """

    name = "paper"
    is_paper = True

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        # 持仓: {symbol: {"side": "long", "quantity": ..., "entry_price": ...}}
        self.positions: dict[str, dict] = {}
        # 当前价格: {symbol: price}
        self.prices: dict[str, float] = {}
        # 订单历史
        self.order_history: list[OrderResponse] = []
        # 已实现盈亏
        self.realized_pnl = 0.0

    def set_price(self, symbol: str, price: float):
        """设置某标的的最新价格"""
        self.prices[symbol] = price

    def set_prices(self, prices: dict[str, float]):
        """批量设置价格"""
        self.prices.update(prices)

    async def place_order(self, request: OrderRequest) -> OrderResponse:
        """模拟下单"""
        order_id = str(uuid.uuid4())[:8]
        current_price = self.prices.get(request.symbol)

        if current_price is None:
            return OrderResponse(
                order_id=order_id, symbol=request.symbol,
                side=request.side, order_type=request.order_type,
                quantity=request.quantity, price=request.price,
                status="rejected", message="No price data available"
            )

        # 计算成交价 (市价单 + 滑点)
        if request.order_type == "market":
            if request.side == "buy":
                fill_price = current_price * (1 + self.slippage_rate)
            else:
                fill_price = current_price * (1 - self.slippage_rate)
        elif request.order_type == "limit":
            if request.price is None:
                return OrderResponse(
                    order_id=order_id, symbol=request.symbol,
                    side=request.side, order_type=request.order_type,
                    quantity=request.quantity, price=request.price,
                    status="rejected", message="Limit order requires price"
                )
            # 简化: 限价单如果价格合适就立即成交
            if request.side == "buy" and current_price <= request.price:
                fill_price = request.price
            elif request.side == "sell" and current_price >= request.price:
                fill_price = request.price
            else:
                return OrderResponse(
                    order_id=order_id, symbol=request.symbol,
                    side=request.side, order_type=request.order_type,
                    quantity=request.quantity, price=request.price,
                    status="pending", message="Limit order queued"
                )
        else:
            fill_price = current_price

        # 计算手续费
        cost = fill_price * request.quantity
        commission = cost * self.commission_rate

        # 执行交易
        if request.side == "buy":
            total_cost = cost + commission
            if total_cost > self.cash:
                return OrderResponse(
                    order_id=order_id, symbol=request.symbol,
                    side=request.side, order_type=request.order_type,
                    quantity=request.quantity, price=fill_price,
                    status="rejected", message=f"Insufficient funds: need {total_cost:.2f}, have {self.cash:.2f}"
                )
            self.cash -= total_cost
            self._update_position(request.symbol, "buy", request.quantity, fill_price)
        else:
            pos = self.positions.get(request.symbol)
            if not pos or pos["quantity"] < request.quantity:
                return OrderResponse(
                    order_id=order_id, symbol=request.symbol,
                    side=request.side, order_type=request.order_type,
                    quantity=request.quantity, price=fill_price,
                    status="rejected", message="Insufficient position"
                )
            proceeds = cost - commission
            pnl = (fill_price - pos["entry_price"]) * request.quantity - commission
            self.cash += proceeds
            self.realized_pnl += pnl
            self._update_position(request.symbol, "sell", request.quantity, fill_price)

        response = OrderResponse(
            order_id=order_id, symbol=request.symbol,
            side=request.side, order_type=request.order_type,
            quantity=request.quantity, price=fill_price,
            status="filled", filled_price=fill_price,
            filled_quantity=request.quantity, fee=commission,
        )
        self.order_history.append(response)
        return response

    def _update_position(self, symbol: str, side: str, quantity: float, price: float):
        """更新持仓"""
        if side == "buy":
            if symbol in self.positions:
                pos = self.positions[symbol]
                # 加仓: 平均成本
                total_qty = pos["quantity"] + quantity
                pos["entry_price"] = (
                    (pos["entry_price"] * pos["quantity"] + price * quantity) / total_qty
                )
                pos["quantity"] = total_qty
            else:
                self.positions[symbol] = {
                    "side": "long",
                    "quantity": quantity,
                    "entry_price": price,
                }
        else:
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos["quantity"] -= quantity
                if pos["quantity"] <= 1e-10:
                    del self.positions[symbol]

    async def cancel_order(self, order_id: str) -> bool:
        return True  # Paper trading: always succeed

    async def get_positions(self) -> list[PositionInfo]:
        result = []
        for symbol, pos in self.positions.items():
            current_price = self.prices.get(symbol, pos["entry_price"])
            unrealized_pnl = (current_price - pos["entry_price"]) * pos["quantity"]
            result.append(PositionInfo(
                symbol=symbol,
                side=pos["side"],
                quantity=pos["quantity"],
                entry_price=pos["entry_price"],
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
            ))
        return result

    async def get_account(self) -> AccountInfo:
        positions_value = sum(
            self.prices.get(sym, pos["entry_price"]) * pos["quantity"]
            for sym, pos in self.positions.items()
        )
        unrealized_pnl = sum(
            (self.prices.get(sym, pos["entry_price"]) - pos["entry_price"]) * pos["quantity"]
            for sym, pos in self.positions.items()
        )
        return AccountInfo(
            total_equity=self.cash + positions_value,
            available_cash=self.cash,
            positions_value=positions_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=self.realized_pnl,
        )

    async def get_ticker(self, symbol: str) -> dict:
        price = self.prices.get(symbol, 0)
        return {"bid": price * 0.9999, "ask": price * 1.0001, "last": price, "volume": 0}
