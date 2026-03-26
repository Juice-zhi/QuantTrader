"""
交易 API - 交易执行, 持仓查询, PnL统计
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import get_session
from app.execution.manager import ExecutionManager
from app.execution.paper import PaperExchange

router = APIRouter(prefix="/api/trading", tags=["Trading"])

# 全局执行管理器 (应用启动时初始化)
_execution_manager: Optional[ExecutionManager] = None


def get_execution_manager() -> ExecutionManager:
    global _execution_manager
    if _execution_manager is None:
        _execution_manager = ExecutionManager()
        # 默认创建一个模拟交易所
        paper = _execution_manager.create_paper_exchange("paper", 100000)
    return _execution_manager


@router.get("/exchanges")
async def list_exchanges():
    """列出已注册的交易所"""
    manager = get_execution_manager()
    return {
        "exchanges": [
            {
                "name": name,
                "is_paper": ex.is_paper,
                "type": ex.name,
            }
            for name, ex in manager.exchanges.items()
        ]
    }


class SetPriceRequest(BaseModel):
    symbol: str
    price: float
    exchange: str = "paper"


@router.post("/set-price")
async def set_price(req: SetPriceRequest):
    """设置模拟价格 (仅Paper Trading)"""
    manager = get_execution_manager()
    exchange = manager.get_exchange(req.exchange)
    if not exchange or not exchange.is_paper:
        return {"error": "Exchange not found or not a paper exchange"}
    exchange.set_price(req.symbol, req.price)
    return {"message": f"Price set: {req.symbol} = {req.price}"}


class ExecuteSignalRequest(BaseModel):
    exchange: str = "paper"
    symbol: str
    signal: int  # 1=buy, -1=sell
    quantity: float
    strategy_id: Optional[int] = None


@router.post("/execute")
async def execute_signal(req: ExecuteSignalRequest):
    """执行交易信号"""
    manager = get_execution_manager()
    response = await manager.execute_signal(
        req.exchange, req.symbol, req.signal, req.quantity, req.strategy_id
    )
    if response is None:
        return {"message": "No action (signal=0)"}
    return {
        "order_id": response.order_id,
        "status": response.status,
        "filled_price": response.filled_price,
        "filled_quantity": response.filled_quantity,
        "fee": response.fee,
        "message": response.message,
    }


@router.get("/portfolio")
async def get_portfolio(exchange: str = Query("paper")):
    """获取账户组合概览"""
    manager = get_execution_manager()
    return await manager.get_portfolio_summary(exchange)


@router.get("/active-strategies")
async def get_active_strategies():
    """获取所有活跃策略"""
    manager = get_execution_manager()
    return {"strategies": manager.get_active_strategies()}
