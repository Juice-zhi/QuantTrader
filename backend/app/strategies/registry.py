"""
策略注册中心
"""
from typing import Type, Optional

from app.strategies.base import BaseStrategy


class StrategyRegistry:
    """策略注册中心"""

    _strategies: dict[str, Type[BaseStrategy]] = {}

    @classmethod
    def register(cls, strategy_cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
        cls._strategies[strategy_cls.__name__] = strategy_cls
        return strategy_cls

    @classmethod
    def create(cls, name: str, **params) -> BaseStrategy:
        strategy_cls = cls._strategies.get(name)
        if strategy_cls is None:
            raise ValueError(f"策略 '{name}' 未注册. 可用策略: {list(cls._strategies.keys())}")
        return strategy_cls(**params)

    @classmethod
    def list_all(cls) -> list[dict]:
        result = []
        for name, scls in cls._strategies.items():
            try:
                instance = scls()
                result.append(instance.info())
            except Exception:
                result.append({"name": name})
        return result

    @classmethod
    def get_class(cls, name: str) -> Optional[Type[BaseStrategy]]:
        return cls._strategies.get(name)
