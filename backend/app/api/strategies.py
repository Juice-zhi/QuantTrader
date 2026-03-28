"""
策略 API - 策略管理, 配置, 启停, 参数编辑
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
from app.strategies import mean_reversion, momentum_strategy, factor_combo, grid_trading, dual_ma, price_action, ict_strategy, trend_following, lgbm_strategy

router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


@router.get("/types")
async def list_strategy_types():
    """列出所有可用策略类型, 包含完整参数schema"""
    return {"strategies": StrategyRegistry.list_all()}


@router.get("/types/{strategy_type}/param-schema")
async def get_param_schema(strategy_type: str):
    """
    获取指定策略类型的完整参数schema

    返回每个参数的: key, label, type, default, min, max, step
    用于前端编辑器生成滑块/输入框
    """
    try:
        instance = StrategyRegistry.create(strategy_type)
        return {
            "strategy_type": strategy_type,
            "name": instance.name,
            "description": instance.description,
            "param_schema": instance.get_param_schema(),
        }
    except ValueError as e:
        return {"error": str(e)}


@router.get("/")
async def list_strategies(
    session: AsyncSession = Depends(get_session),
):
    """列出所有已配置的策略, 附带param_schema供编辑器使用"""
    result = await session.execute(select(StrategyModel).order_by(StrategyModel.id.desc()))
    strategies = result.scalars().all()

    items = []
    for s in strategies:
        item = {
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

        # Attach param_schema from the strategy class for the editor
        try:
            # Create instance with current DB params to get schema with current values
            instance = StrategyRegistry.create(s.strategy_type, **s.params)
            item["param_schema"] = instance.get_param_schema()
        except Exception:
            item["param_schema"] = []

        items.append(item)

    return {"strategies": items}


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

    # 合并默认参数 + 用户参数
    try:
        instance = StrategyRegistry.create(req.strategy_type, **req.params)
        merged_params = instance.params  # BaseStrategy.__init__ does the merge
    except Exception:
        merged_params = req.params

    strategy = StrategyModel(
        name=req.name,
        strategy_type=req.strategy_type,
        params=merged_params,
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
    """更新策略配置 - 支持部分参数更新"""
    result = await session.execute(select(StrategyModel).where(StrategyModel.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        return {"error": "Strategy not found"}

    if req.params is not None:
        # 部分更新: 合并现有参数 + 新参数
        existing_params = strategy.params or {}
        merged = {**existing_params, **req.params}

        # 验证参数范围 (如果策略定义了param_space)
        warnings = []
        try:
            instance = StrategyRegistry.create(strategy.strategy_type)
            space = instance.param_space()
            for key, val in req.params.items():
                if key in space and isinstance(val, (int, float)):
                    mn, mx, step = space[key]
                    if val < mn or val > mx:
                        warnings.append(f"{key}={val} out of range [{mn}, {mx}]")
        except Exception:
            pass

        strategy.params = merged

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

    response = {"message": "Strategy updated", "params": strategy.params}
    if req.params is not None and 'warnings' in dir() and warnings:
        response["warnings"] = warnings
    return response


@router.put("/{strategy_id}/params/{param_key}")
async def update_single_param(
    strategy_id: int,
    param_key: str,
    value: float = Query(..., description="New parameter value"),
    session: AsyncSession = Depends(get_session),
):
    """
    更新单个参数 - 最轻量的运行时调整接口

    PUT /api/strategies/1/params/trend_ema?value=55
    """
    result = await session.execute(select(StrategyModel).where(StrategyModel.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        return {"error": "Strategy not found"}

    params = strategy.params or {}
    old_value = params.get(param_key)
    params[param_key] = value
    strategy.params = params

    return {
        "message": f"Parameter '{param_key}' updated",
        "param": param_key,
        "old_value": old_value,
        "new_value": value,
    }


@router.post("/{strategy_id}/reset-params")
async def reset_params(
    strategy_id: int,
    session: AsyncSession = Depends(get_session),
):
    """重置策略参数到默认值"""
    result = await session.execute(select(StrategyModel).where(StrategyModel.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        return {"error": "Strategy not found"}

    try:
        instance = StrategyRegistry.create(strategy.strategy_type)
        strategy.params = instance.default_params.copy()
        return {"message": "Parameters reset to defaults", "params": strategy.params}
    except Exception as e:
        return {"error": f"Cannot reset: {e}"}


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
