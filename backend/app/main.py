"""
QuantTrader - 量化交易系统 API 入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.engine import init_db, close_db
from app.api.data import router as data_router
from app.api.factors import router as factors_router
from app.api.strategies import router as strategies_router
from app.api.backtest import router as backtest_router
from app.api.trading import router as trading_router
from app.api.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    await init_db()
    print(f"🚀 QuantTrader v{settings.VERSION} started")
    print(f"📊 Database: {settings.DATABASE_URL}")
    yield
    # Shutdown
    await close_db()
    print("👋 QuantTrader shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="全栈量化交易系统 - 因子库 + 策略引擎 + 回测 + 实盘交易",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(data_router)
app.include_router(factors_router)
app.include_router(strategies_router)
app.include_router(backtest_router)
app.include_router(trading_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "endpoints": {
            "data": "/api/data",
            "factors": "/api/factors",
            "strategies": "/api/strategies",
            "backtest": "/api/backtest",
            "trading": "/api/trading",
            "websocket": "/ws",
            "docs": "/docs",
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
