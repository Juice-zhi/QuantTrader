"""
执行管理器 - 统一管理策略执行和交易

功能:
- 一键启停策略
- 路由策略信号到交易所
- 实时 PnL 统计
- 风控检查
"""
import asyncio
from datetime import datetime
from typing import Optional

from app.execution.base import BaseExchange, OrderRequest, OrderResponse, AccountInfo
from app.execution.paper import PaperExchange
from app.execution.ccxt_exchange import CCXTExchange
from app.strategies.base import BaseStrategy


class RiskManager:
    """风控管理"""

    def __init__(
        self,
        max_loss_pct: float = 0.10,        # 最大亏损比例
        max_position_pct: float = 0.30,     # 单标的最大仓位比例
        max_daily_trades: int = 50,         # 日最大交易次数
        max_order_size: float = 0.10,       # 单笔最大下单比例
    ):
        self.max_loss_pct = max_loss_pct
        self.max_position_pct = max_position_pct
        self.max_daily_trades = max_daily_trades
        self.max_order_size = max_order_size
        self.daily_trades = 0
        self.last_reset_date = datetime.utcnow().date()

    def check_order(self, request: OrderRequest, account: AccountInfo) -> tuple[bool, str]:
        """检查订单是否通过风控"""
        today = datetime.utcnow().date()
        if today != self.last_reset_date:
            self.daily_trades = 0
            self.last_reset_date = today

        # 日交易次数限制
        if self.daily_trades >= self.max_daily_trades:
            return False, f"Daily trade limit reached ({self.max_daily_trades})"

        # 最大亏损
        if account.total_equity > 0:
            loss_pct = -account.unrealized_pnl / account.total_equity
            if loss_pct > self.max_loss_pct:
                return False, f"Max loss exceeded ({loss_pct:.1%} > {self.max_loss_pct:.1%})"

        # 单笔下单大小
        if account.total_equity > 0 and request.quantity > 0:
            order_value = request.quantity * (request.price or 0)
            if order_value / account.total_equity > self.max_order_size:
                return False, f"Order too large ({order_value / account.total_equity:.1%} of equity)"

        self.daily_trades += 1
        return True, "OK"


class ExecutionManager:
    """
    执行管理器

    用法:
        manager = ExecutionManager()
        manager.add_exchange("paper", PaperExchange(100000))
        manager.add_exchange("binance", CCXTExchange("binance"))

        # 执行信号
        response = await manager.execute_signal("paper", signal_row)
    """

    def __init__(self):
        self.exchanges: dict[str, BaseExchange] = {}
        self.risk_manager = RiskManager()
        # 策略运行状态: {strategy_id: {"running": True, "exchange": "paper", ...}}
        self.active_strategies: dict[int, dict] = {}
        # 交易统计
        self.trade_stats: dict[int, dict] = {}

    def add_exchange(self, name: str, exchange: BaseExchange):
        """注册交易所"""
        self.exchanges[name] = exchange

    def get_exchange(self, name: str) -> Optional[BaseExchange]:
        return self.exchanges.get(name)

    def create_paper_exchange(
        self,
        name: str = "paper",
        initial_capital: float = 100000.0,
    ) -> PaperExchange:
        """创建并注册模拟交易所"""
        exchange = PaperExchange(initial_capital=initial_capital)
        self.add_exchange(name, exchange)
        return exchange

    def create_live_exchange(
        self,
        exchange_name: str,
        sandbox: bool = False,
    ) -> CCXTExchange:
        """创建并注册实盘交易所"""
        exchange = CCXTExchange(exchange_name, sandbox=sandbox)
        self.add_exchange(exchange_name, exchange)
        return exchange

    async def execute_signal(
        self,
        exchange_name: str,
        symbol: str,
        signal: int,
        quantity: float,
        strategy_id: Optional[int] = None,
    ) -> Optional[OrderResponse]:
        """
        执行交易信号

        Args:
            exchange_name: 交易所名称
            symbol: 交易标的
            signal: 1=买入, -1=卖出, 0=无操作
            quantity: 数量
            strategy_id: 策略ID
        """
        if signal == 0:
            return None

        exchange = self.exchanges.get(exchange_name)
        if exchange is None:
            raise ValueError(f"Exchange '{exchange_name}' not registered")

        side = "buy" if signal == 1 else "sell"
        request = OrderRequest(
            symbol=symbol,
            side=side,
            order_type="market",
            quantity=quantity,
            strategy_id=strategy_id,
        )

        # 风控检查
        account = await exchange.get_account()
        passed, reason = self.risk_manager.check_order(request, account)
        if not passed:
            return OrderResponse(
                order_id="", symbol=symbol, side=side,
                order_type="market", quantity=quantity, price=None,
                status="rejected", message=f"Risk check failed: {reason}"
            )

        # 执行订单
        response = await exchange.place_order(request)

        # 更新统计
        if strategy_id is not None:
            if strategy_id not in self.trade_stats:
                self.trade_stats[strategy_id] = {
                    "total_trades": 0, "winning_trades": 0, "total_pnl": 0
                }
            self.trade_stats[strategy_id]["total_trades"] += 1

        return response

    async def get_portfolio_summary(self, exchange_name: str) -> dict:
        """获取账户组合概览"""
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return {}

        account = await exchange.get_account()
        positions = await exchange.get_positions()

        return {
            "exchange": exchange_name,
            "is_paper": exchange.is_paper,
            "total_equity": account.total_equity,
            "available_cash": account.available_cash,
            "positions_value": account.positions_value,
            "unrealized_pnl": account.unrealized_pnl,
            "realized_pnl": account.realized_pnl,
            "positions": [
                {
                    "symbol": p.symbol,
                    "side": p.side,
                    "quantity": p.quantity,
                    "entry_price": p.entry_price,
                    "current_price": p.current_price,
                    "unrealized_pnl": p.unrealized_pnl,
                }
                for p in positions
            ],
        }

    def start_strategy(self, strategy_id: int, exchange_name: str, strategy: BaseStrategy):
        """启动策略"""
        self.active_strategies[strategy_id] = {
            "running": True,
            "exchange": exchange_name,
            "strategy": strategy,
            "started_at": datetime.utcnow().isoformat(),
        }

    def stop_strategy(self, strategy_id: int):
        """停止策略"""
        if strategy_id in self.active_strategies:
            self.active_strategies[strategy_id]["running"] = False

    def get_active_strategies(self) -> dict:
        """获取所有活跃策略"""
        return {
            sid: {
                "running": info["running"],
                "exchange": info["exchange"],
                "strategy_name": info["strategy"].name,
                "started_at": info["started_at"],
            }
            for sid, info in self.active_strategies.items()
        }

    async def close_all(self):
        """关闭所有交易所连接"""
        for exchange in self.exchanges.values():
            await exchange.close()
