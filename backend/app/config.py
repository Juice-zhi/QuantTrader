"""
QuantTrader 配置管理
支持通过环境变量或 .env 文件配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """全局配置"""

    # 项目
    PROJECT_NAME: str = "QuantTrader"
    VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # 数据库 - 默认 SQLite (开发), 可切换 PostgreSQL (生产)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'quanttrader.db'}"
    )

    # 同步数据库 URL (用于 alembic 等需要同步访问的场景)
    @property
    def SYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if "aiosqlite" in url:
            return url.replace("sqlite+aiosqlite", "sqlite")
        if "asyncpg" in url:
            return url.replace("postgresql+asyncpg", "postgresql")
        return url

    # API Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # 交易所 API Keys
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET: str = os.getenv("BINANCE_SECRET", "")

    OKX_API_KEY: str = os.getenv("OKX_API_KEY", "")
    OKX_SECRET: str = os.getenv("OKX_SECRET", "")
    OKX_PASSPHRASE: str = os.getenv("OKX_PASSPHRASE", "")

    BYBIT_API_KEY: str = os.getenv("BYBIT_API_KEY", "")
    BYBIT_SECRET: str = os.getenv("BYBIT_SECRET", "")

    # IBKR
    IBKR_HOST: str = os.getenv("IBKR_HOST", "127.0.0.1")
    IBKR_PORT: int = int(os.getenv("IBKR_PORT", "7497"))
    IBKR_CLIENT_ID: int = int(os.getenv("IBKR_CLIENT_ID", "1"))

    # 数据目录
    DATA_DIR: Path = BASE_DIR / "data"

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
