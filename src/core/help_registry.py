"""
帮助文本注册系统
允许模块通过 decorator 在 handle 函数上直接定义帮助文本
"""
from typing import Dict, Optional, Callable, Any
from functools import wraps
import inspect


class HelpRegistry:
    """帮助文本注册表"""
    _registry: Dict[str, str] = {}
    _admin_registry: Dict[str, str] = {}
    
    @classmethod
    def register(cls, module_name: str, help_text: str, is_admin: bool = False):
        """
        注册模块的帮助文本
        
        Args:
            module_name: 模块名称
            help_text: 帮助文本内容
            is_admin: 是否为管理员专用帮助
        """
        if is_admin:
            cls._admin_registry[module_name] = help_text
        else:
            cls._registry[module_name] = help_text
    
    @classmethod
    def get_help(cls, module_name: str, is_admin: bool = False) -> Optional[str]:
        """
        获取模块的帮助文本
        
        Args:
            module_name: 模块名称
            is_admin: 是否为管理员专用帮助
            
        Returns:
            帮助文本，如果不存在则返回 None
        """
        if is_admin:
            return cls._admin_registry.get(module_name)
        return cls._registry.get(module_name)
    
    @classmethod
    def get_all_helps(cls) -> Dict[str, str]:
        """获取所有非管理员帮助文本"""
        return cls._registry.copy()
    
    @classmethod
    def get_all_admin_helps(cls) -> Dict[str, str]:
        """获取所有管理员帮助文本"""
        return cls._admin_registry.copy()
    
    @classmethod
    def clear(cls):
        """清空注册表（主要用于测试）"""
        cls._registry.clear()
        cls._admin_registry.clear()


def with_help(module_name: str, is_admin: bool = False):
    """
    装饰器：为 handle 函数添加帮助文本
    帮助文本从函数的 docstring 中获取
    
    使用方式：
       @with_help("模块名")
       @handler.handle()
       async def handle_xxx():
           \"\"\"帮助文本内容\"\"\"
           ...
    
    管理员帮助文本：
       @with_help("模块名", is_admin=True)
       @admin_handler.handle()
       async def handle_admin():
           \"\"\"管理员帮助文本内容\"\"\"
           ...
    
    Args:
        module_name: 模块名称
        is_admin: 是否为管理员专用帮助
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        # 从函数 docstring 获取帮助文本
        text = inspect.getdoc(func)
        if text is None:
            text = ""
        
        # 注册帮助文本
        if text.strip():  # 只有非空文本才注册
            HelpRegistry.register(module_name, text.strip(), is_admin)
        
        # 保持原函数不变
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

