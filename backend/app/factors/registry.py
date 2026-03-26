"""
因子注册中心 - 自动发现和管理所有因子

使用装饰器模式:
    @FactorRegistry.register
    class RSI(BaseFactor):
        ...

查询因子:
    FactorRegistry.get("RSI_14")
    FactorRegistry.list_by_category("technical")
"""
from typing import Type, Optional

from app.factors.base import BaseFactor


class FactorRegistry:
    """因子注册中心 - 单例模式"""

    _factors: dict[str, Type[BaseFactor]] = {}
    _instances: dict[str, BaseFactor] = {}

    @classmethod
    def register(cls, factor_cls: Type[BaseFactor]) -> Type[BaseFactor]:
        """
        装饰器: 注册因子类

        @FactorRegistry.register
        class MyFactor(BaseFactor):
            ...
        """
        key = factor_cls.__name__
        cls._factors[key] = factor_cls
        return factor_cls

    @classmethod
    def get_class(cls, name: str) -> Optional[Type[BaseFactor]]:
        """获取因子类"""
        return cls._factors.get(name)

    @classmethod
    def create(cls, name: str, **params) -> BaseFactor:
        """创建因子实例"""
        factor_cls = cls._factors.get(name)
        if factor_cls is None:
            raise ValueError(f"因子 '{name}' 未注册. 可用因子: {list(cls._factors.keys())}")
        instance = factor_cls(**params)
        cls._instances[instance.name] = instance
        return instance

    @classmethod
    def get_instance(cls, instance_name: str) -> Optional[BaseFactor]:
        """获取已创建的因子实例"""
        return cls._instances.get(instance_name)

    @classmethod
    def list_all(cls) -> list[dict]:
        """列出所有注册的因子"""
        result = []
        for name, factor_cls in cls._factors.items():
            # 创建一个默认实例获取 info
            try:
                instance = factor_cls()
                result.append({
                    "class_name": name,
                    "category": instance.category,
                    "description": instance.description,
                })
            except TypeError:
                result.append({
                    "class_name": name,
                    "category": getattr(factor_cls, "category", "unknown"),
                    "description": getattr(factor_cls, "description", ""),
                })
        return result

    @classmethod
    def list_by_category(cls, category: str) -> list[dict]:
        """按类别列出因子"""
        return [f for f in cls.list_all() if f["category"] == category]

    @classmethod
    def categories(cls) -> list[str]:
        """获取所有因子类别"""
        return list(set(f["category"] for f in cls.list_all()))

    @classmethod
    def clear(cls):
        """清空注册 (测试用)"""
        cls._factors.clear()
        cls._instances.clear()
