"""
策略 API - 策略管理, 配置, 启停
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import get_session
from app.database.models import Strategy as StrategyModel, StrategyStatus, ExecutionMode
from app.strategies.registry import StrategyRegistry

# 触发策略注册
from app.strategies import mean_reversion, momentum_strategy, factor_combo, grid_trading, dual_ma

router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


@router.get("/types")
async def list_strategy_types():
    """列出所有可用策略类型"""
    return {"strategies": StrategyRegistry.list_all()}


@router.get("/")
async def list_strategies(
    session: AsyncSession = Depends(get_session),
):
    """列出所有已配置的策略"""
    result = await session.execute(select(StrategyModel).order_by(StrategyModel.id.desc()))
    strategies = result.scalars().all()
    return {
        "strategies": [
            {
                "id": s.id,
                "name": s.name,
                "strategy_type": s.strategy_type,
                "params": s.params,
                "status": s.status.value if s.status else "inactive",
                "execution_mode": s.execution_mode.value if s.execution_mode else "paper",
                "exchange": s.exchange,
                "is_enabled": s.is_enabled,
                "created_at": str(s.created_at),
            }
            for s in strategies
        ]
    }


class CreateStrategyRequest(BaseModel):
    name: str
    strategy_type: str
    params: dict = {}
    exchange: Optional[str] = None
    symbols_config: Optional[list] = None
    execution_mode: str = "paper"


@router.post("/")
async def create_strategy(
    req: CreateStrategyRequest,
    session: AsyncSession = Depends(get_session),
):
    """创建新策略"""
    # 验证策略类型
    if not StrategyRegistry.get_class(req.strategy_type):
        return {"error": f"Unknown strategy type: {req.strategy_type}"}

    strategy = StrategyModel(
        name=req.name,
        strategy_type=req.strategy_type,
        params=req.params,
        exchange=req.exchange,
        symbols_config=req.symbols_config,
        execution_mode=ExecutionMode(req.execution_mode),
        status=StrategyStatus.INACTIVE,
    )
    session.add(strategy)
    await session.flush()
    return {"id": strategy.id, "message": "Strategy created"}


class UpdateStrategyRequest(BaseModel):
    params: Optional[dict] = None
    is_enabled: Optional[bool] = None
    exchange: Optional[str] = None
    execution_mode: Optional[str] = None


@router.put("/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    req: UpdateStrategyRequest,
    session: AsyncSession = Depends(get_session),
):
    """更新策略配置"""
    result = await session.execute(select(StrategyModel).where(StrategyModel.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        return {"error": "Strategy not found"}

    if req.params is not None:
        strategy.params = req.params
    if req.is_enabled is not None:
        strategy.is_enabled = req.is_enabled
        strategy.status = (
            StrategyStatus.PAPER_TRADING if req.is_enabled
            else StrategyStatus.INACTIVE
        )
    if req.exchange is not None:
        strategy.exchange = req.exchange
    if req.execution_mode is not None:
        strategy.execution_mode = ExecutionMode(req.execution_mode)

    return {"message": "Strategy updated"}


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_session),
):
    """删除策略"""
    result = await session.execute(select(StrategyModel).where(StrategyModel.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        return {"error": "Strategy not found"}
    await session.delete(strategy)
    return {"message": "Strategy deleted"}
