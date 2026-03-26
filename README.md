# QuantTrader - 全栈量化交易系统

一个完整的量化交易框架，包含因子库、策略引擎、回测系统、交易执行层和 Web/桌面控制台。

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Electron)               │
│  Dashboard │ Strategies │ Factors │ Backtest │ Trading       │
├─────────────────────────────────────────────────────────────┤
│                    REST API + WebSocket (FastAPI)             │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  Data    │  Factor  │ Strategy │ Backtest │   Execution     │
│  Layer   │  Library │  Engine  │  Engine  │   Layer         │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│              Database (SQLite / PostgreSQL)                   │
└─────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. 历史数据库 (`backend/app/data/`)

- **多源数据抓取**: ccxt (加密货币 Binance/OKX/Bybit) + yfinance (美股/港股)
- **统一存储**: 12 张表的 ORM 模型，支持多时间粒度 (1m ~ 1w) K线数据
- **DataProvider 统一接口**: 优先从数据库读取，不足时自动从网络抓取并缓存

### 2. 因子库 (`backend/app/factors/`) — 26 个因子

| 分类 | 因子 |
|------|------|
| 技术 (9) | SMA, EMA, RSI, MACD, BollingerBands, ATR, StochasticOscillator, WilliamsR, CCI |
| 动量 (5) | PriceMomentum, RateOfChange, RelativeStrength, MomentumAcceleration, TrendStrength(ADX) |
| 波动率 (5) | HistoricalVolatility, ParkinsonVolatility, GarmanKlassVolatility, VolatilitySkew, VolatilityRatio |
| 量价 (6) | OBV, VWAP, VolumeRatio, MoneyFlowIndex, ForceIndex, VolumeWeightedMomentum |
| 复合 (1) | MultiFactorScore (多因子加权评分) |

**因子分析工具**: IC 值计算、因子相关性矩阵、因子统计信息

### 3. 策略引擎 (`backend/app/strategies/`) — 5 个内置策略

| 策略 | 说明 |
|------|------|
| 均值回归策略 | 布林带 + RSI 超卖超买信号 |
| 动量突破策略 | N日高点突破 + ADX趋势确认 + 放量确认 |
| 多因子组合策略 | RSI + MACD + 动量 + MFI + 量比 五因子加权打分 |
| 网格交易策略 | ATR 动态网格，适合震荡行情 |
| 双均线策略 | EMA 金叉买入、死叉卖出 |

### 4. 回测引擎 (`backend/app/backtest/`)

- 手续费 + 滑点模拟
- 止损机制
- 16 项绩效指标: 年化收益、夏普比率、Sortino、Calmar、最大回撤、胜率、盈亏比等
- 净值曲线 + 完整交易记录

### 5. 交易执行层 (`backend/app/execution/`)

- **Paper Trading**: 完整的模拟交易引擎（市价单/限价单/手续费/滑点/PnL 追踪）
- **实盘连接器**: Binance / OKX / Bybit (通过 ccxt)，IBKR 接口预留
- **风控管理**: 最大亏损限制、单笔下单限制、日交易次数限制
- **ExecutionManager**: 一键启停策略、信号路由、组合概览

### 6. Web Dashboard + Electron 桌面应用 (`frontend/`)

5 个页面: Dashboard 总览 | 策略管理 | 因子库 | 回测 | 交易终端

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- (可选) PostgreSQL — 默认使用 SQLite

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 运行测试（验证安装）

```bash
cd backend
python -m pytest tests/ -v
# 预期: 77 passed
```

---

## 启动方式

### 方式 A: Web 模式（后端 + 前端分别启动）

```bash
# 终端 1 - 启动后端 API (端口 8000)
cd backend
python -m uvicorn app.main:app --reload --port 8000

# 终端 2 - 启动前端 (端口 3000)
cd frontend
npm run dev
```

访问:
- 前端界面: http://localhost:3000
- API 文档 (Swagger): http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### 方式 B: Electron 桌面应用（一键启动）

```bash
cd frontend

# 开发模式 (支持热重载)
npm run electron:dev

# 预览模式 (使用构建产物)
npm run build
npm run electron:preview
```

桌面应用会**自动启动 Python 后端**，无需手动操作。

### 方式 C: 打包成安装包

```bash
cd frontend
npm run electron:build
# 输出在 frontend/release/ 目录
# macOS: .dmg    Windows: .exe    Linux: .AppImage
```

---

## API 端点

| 模块 | 路径 | 说明 |
|------|------|------|
| 数据 | `GET /api/data/ohlcv` | 获取 K 线数据 |
| 数据 | `GET /api/data/symbols` | 获取交易标的列表 |
| 因子 | `GET /api/factors/list` | 列出所有因子 |
| 因子 | `POST /api/factors/compute` | 计算因子值 |
| 因子 | `POST /api/factors/ic` | 计算因子 IC 值 |
| 策略 | `GET /api/strategies/types` | 可用策略类型 |
| 策略 | `GET /api/strategies/` | 已配置策略列表 |
| 策略 | `POST /api/strategies/` | 创建策略 |
| 策略 | `PUT /api/strategies/{id}` | 更新策略 (参数微调/启停) |
| 回测 | `POST /api/backtest/run` | 执行回测 |
| 回测 | `GET /api/backtest/results` | 回测结果列表 |
| 交易 | `POST /api/trading/execute` | 执行交易信号 |
| 交易 | `GET /api/trading/portfolio` | 账户组合概览 |
| 实时 | `WebSocket /ws` | 实时推送 |

完整交互式文档: http://localhost:8000/docs

---

## 项目结构

```
QuantTrader/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── database/
│   │   │   ├── engine.py        # 数据库连接
│   │   │   └── models.py        # 12 张 ORM 表
│   │   ├── data/
│   │   │   ├── fetcher.py       # 多源数据抓取 (ccxt + yfinance)
│   │   │   ├── storage.py       # 数据入库
│   │   │   └── provider.py      # 统一数据接口
│   │   ├── factors/
│   │   │   ├── base.py          # 因子基类
│   │   │   ├── registry.py      # 因子注册中心
│   │   │   ├── technical.py     # 技术因子 (9)
│   │   │   ├── momentum.py      # 动量因子 (5)
│   │   │   ├── volatility.py    # 波动率因子 (5)
│   │   │   ├── volume.py        # 量价因子 (6)
│   │   │   └── composite.py     # 复合因子 + 分析工具
│   │   ├── strategies/
│   │   │   ├── base.py          # 策略基类
│   │   │   ├── registry.py      # 策略注册中心
│   │   │   ├── mean_reversion.py
│   │   │   ├── momentum_strategy.py
│   │   │   ├── factor_combo.py
│   │   │   ├── grid_trading.py
│   │   │   └── dual_ma.py
│   │   ├── backtest/
│   │   │   ├── engine.py        # 回测引擎
│   │   │   └── metrics.py       # 16 项绩效指标
│   │   ├── execution/
│   │   │   ├── base.py          # 交易所基类
│   │   │   ├── paper.py         # 模拟交易引擎
│   │   │   ├── ccxt_exchange.py # Binance/OKX/Bybit
│   │   │   └── manager.py       # 执行管理器 + 风控
│   │   └── api/                 # REST API 路由
│   ├── tests/                   # 77 个自动化测试
│   └── requirements.txt
├── frontend/
│   ├── electron/
│   │   ├── main.cjs             # Electron 主进程
│   │   └── preload.cjs          # 安全桥接
│   ├── src/
│   │   ├── App.tsx              # 路由 + 布局
│   │   ├── pages/               # 5 个页面
│   │   └── services/api.ts      # API 调用层
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## 扩展指南

### 添加新因子

```python
# backend/app/factors/technical.py (或新建文件)
from app.factors.base import BaseFactor
from app.factors.registry import FactorRegistry

@FactorRegistry.register
class MyFactor(BaseFactor):
    category = "technical"
    description = "我的自定义因子"

    def __init__(self, period: int = 20):
        super().__init__(period=period)
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(self.period).mean()  # 你的计算逻辑
```

### 添加新策略

```python
# backend/app/strategies/my_strategy.py
from app.strategies.base import BaseStrategy
from app.strategies.registry import StrategyRegistry

@StrategyRegistry.register
class MyStrategy(BaseStrategy):
    name = "我的策略"
    description = "策略描述"
    default_params = {"param1": 10}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df[["timestamp", "close"]].copy()
        result["signal"] = 0  # 1=买, -1=卖, 0=持有
        # 你的信号逻辑
        return result
```

### 切换到 PostgreSQL

```bash
# .env 文件
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/quanttrader
```

### 配置交易所 API

```bash
# backend/.env
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret
OKX_API_KEY=your_key
OKX_SECRET=your_secret
OKX_PASSPHRASE=your_passphrase
```

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| ORM | SQLAlchemy 2.0 (async) |
| 数据源 | ccxt (加密货币) + yfinance (股票) |
| 因子计算 | pandas + numpy |
| 前端 | React 19 + TypeScript + Vite |
| UI | TailwindCSS + Recharts + Lucide Icons |
| 桌面应用 | Electron |
| 测试 | pytest + pytest-asyncio |
