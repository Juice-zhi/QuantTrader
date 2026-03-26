"""
QuantTrader 数据库模型

核心表设计:
- Symbol: 交易标的 (股票/加密货币)
- OHLCV: K线数据 (支持多时间粒度)
- FactorMeta / FactorValue: 因子元数据和计算缓存
- Strategy / StrategyConfig: 策略配置
- BacktestResult: 回测结果
- Order / Trade / Position: 交易相关
- PortfolioSnapshot: 组合净值快照
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Float, Integer, Boolean, DateTime, Text, JSON,
    ForeignKey, UniqueConstraint, Index, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.engine import Base


# ──────────────────── 枚举类型 ────────────────────


class MarketType(str, enum.Enum):
    CRYPTO = "crypto"
    US_STOCK = "us_stock"
    CN_STOCK = "cn_stock"
    HK_STOCK = "hk_stock"
    FUTURES = "futures"


class TimeFrame(str, enum.Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class StrategyStatus(str, enum.Enum):
    INACTIVE = "inactive"
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"


class ExecutionMode(str, enum.Enum):
    PAPER = "paper"
    LIVE = "live"


# ──────────────────── 市场数据表 ────────────────────


class Symbol(Base):
    """交易标的"""
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), comment="标的名称, e.g. BTC/USDT, AAPL")
    market_type: Mapped[MarketType] = mapped_column(SAEnum(MarketType))
    exchange: Mapped[str] = mapped_column(String(50), comment="交易所, e.g. binance, nasdaq")
    base_currency: Mapped[str] = mapped_column(String(20), comment="基础货币, e.g. BTC, AAPL")
    quote_currency: Mapped[str] = mapped_column(String(20), comment="计价货币, e.g. USDT, USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    ohlcv_data: Mapped[list["OHLCV"]] = relationship(back_populates="symbol", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("name", "exchange", name="uq_symbol_exchange"),
    )


class OHLCV(Base):
    """K线数据 - 支持多时间粒度"""
    __tablename__ = "ohlcv"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), index=True)
    timeframe: Mapped[TimeFrame] = mapped_column(SAEnum(TimeFrame))
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)

    # Relationships
    symbol: Mapped["Symbol"] = relationship(back_populates="ohlcv_data")

    __table_args__ = (
        UniqueConstraint("symbol_id", "timeframe", "timestamp", name="uq_ohlcv_key"),
        Index("ix_ohlcv_lookup", "symbol_id", "timeframe", "timestamp"),
    )


# ──────────────────── 因子表 ────────────────────


class FactorMeta(Base):
    """因子元数据"""
    __tablename__ = "factor_meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, comment="因子名称, e.g. RSI_14")
    category: Mapped[str] = mapped_column(String(50), comment="因子类别: technical, momentum, volatility, volume, composite")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="因子参数")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    values: Mapped[list["FactorValue"]] = relationship(back_populates="factor", cascade="all, delete-orphan")


class FactorValue(Base):
    """因子计算结果缓存"""
    __tablename__ = "factor_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    factor_id: Mapped[int] = mapped_column(ForeignKey("factor_meta.id"), index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), index=True)
    timeframe: Mapped[TimeFrame] = mapped_column(SAEnum(TimeFrame))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    value: Mapped[float] = mapped_column(Float)

    # Relationships
    factor: Mapped["FactorMeta"] = relationship(back_populates="values")

    __table_args__ = (
        UniqueConstraint("factor_id", "symbol_id", "timeframe", "timestamp", name="uq_factor_value_key"),
        Index("ix_factor_lookup", "factor_id", "symbol_id", "timeframe", "timestamp"),
    )


# ──────────────────── 策略表 ────────────────────


class Strategy(Base):
    """策略配置"""
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), comment="策略名称")
    strategy_type: Mapped[str] = mapped_column(String(100), comment="策略类型(类名)")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict, comment="策略参数")
    status: Mapped[StrategyStatus] = mapped_column(
        SAEnum(StrategyStatus), default=StrategyStatus.INACTIVE
    )
    execution_mode: Mapped[ExecutionMode] = mapped_column(
        SAEnum(ExecutionMode), default=ExecutionMode.PAPER
    )
    exchange: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="绑定交易所")
    symbols_config: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, comment="交易标的配置")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    backtest_results: Mapped[list["BacktestResult"]] = relationship(back_populates="strategy", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="strategy", cascade="all, delete-orphan")
    positions: Mapped[list["Position"]] = relationship(back_populates="strategy", cascade="all, delete-orphan")


# ──────────────────── 回测表 ────────────────────


class BacktestResult(Base):
    """回测结果"""
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id"), index=True)
    symbol_name: Mapped[str] = mapped_column(String(50))
    timeframe: Mapped[TimeFrame] = mapped_column(SAEnum(TimeFrame))
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    initial_capital: Mapped[float] = mapped_column(Float)
    final_capital: Mapped[float] = mapped_column(Float)

    # 绩效指标
    total_return: Mapped[float] = mapped_column(Float, comment="总收益率")
    annual_return: Mapped[float] = mapped_column(Float, comment="年化收益率")
    sharpe_ratio: Mapped[float] = mapped_column(Float, comment="夏普比率")
    max_drawdown: Mapped[float] = mapped_column(Float, comment="最大回撤")
    win_rate: Mapped[float] = mapped_column(Float, comment="胜率")
    profit_factor: Mapped[float] = mapped_column(Float, comment="盈亏比")
    total_trades: Mapped[int] = mapped_column(Integer, comment="总交易次数")

    # 详细数据 (JSON)
    equity_curve: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, comment="净值曲线")
    trade_log: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, comment="交易记录")
    params_used: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="使用的参数")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    strategy: Mapped["Strategy"] = relationship(back_populates="backtest_results")


# ──────────────────── 交易表 ────────────────────


class Order(Base):
    """订单记录"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id"), index=True)
    symbol_name: Mapped[str] = mapped_column(String(50))
    exchange: Mapped[str] = mapped_column(String(50))
    execution_mode: Mapped[ExecutionMode] = mapped_column(SAEnum(ExecutionMode))

    side: Mapped[OrderSide] = mapped_column(SAEnum(OrderSide))
    order_type: Mapped[OrderType] = mapped_column(SAEnum(OrderType))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="限价单价格")
    filled_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    filled_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.PENDING)
    exchange_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fee: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    strategy: Mapped["Strategy"] = relationship(back_populates="orders")
    trades: Mapped[list["Trade"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class Trade(Base):
    """成交记录"""
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    symbol_name: Mapped[str] = mapped_column(String(50))
    side: Mapped[OrderSide] = mapped_column(SAEnum(OrderSide))
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="本笔交易盈亏")
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="trades")


class Position(Base):
    """当前持仓"""
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id"), index=True)
    symbol_name: Mapped[str] = mapped_column(String(50))
    exchange: Mapped[str] = mapped_column(String(50))
    side: Mapped[OrderSide] = mapped_column(SAEnum(OrderSide))
    quantity: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    strategy: Mapped["Strategy"] = relationship(back_populates="positions")

    __table_args__ = (
        UniqueConstraint("strategy_id", "symbol_name", "exchange", "side", name="uq_position_key"),
    )


class PortfolioSnapshot(Base):
    """组合净值快照 - 定时记录"""
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategies.id"), nullable=True, index=True)
    total_equity: Mapped[float] = mapped_column(Float, comment="总权益")
    cash: Mapped[float] = mapped_column(Float, comment="可用资金")
    positions_value: Mapped[float] = mapped_column(Float, comment="持仓市值")
    daily_pnl: Mapped[float] = mapped_column(Float, default=0.0, comment="日盈亏")
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0, comment="累计盈亏")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
