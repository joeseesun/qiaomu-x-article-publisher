"""
==============================================================================
Browser Authentication Framework - 通用浏览器认证框架
==============================================================================

PURPOSE:
  支持多网站配置驱动的认证管理，解决 Playwright session cookie bug

CORE COMPONENTS:
  - SiteConfig: 配置驱动的验证策略
  - BrowserAuthManager: 通用认证管理器（核心类）
  - BrowserFactory: 浏览器实例工厂

SOLUTION:
  混合认证方案 (user_data_dir + state.json 手动注入)
  解决 Playwright #36139: Session cookies 持久化问题
"""

from .config import SiteConfig, DEFAULT_BROWSER_ARGS, DEFAULT_USER_AGENT
from .browser_factory import BrowserFactory
from .auth_manager import BrowserAuthManager
from .exceptions import (
    BrowserAuthError,
    AuthenticationError,
    ValidationError,
    ConfigurationError,
    StateFileError
)

__version__ = "1.0.0"

__all__ = [
    'SiteConfig',
    'BrowserFactory',
    'BrowserAuthManager',
    'DEFAULT_BROWSER_ARGS',
    'DEFAULT_USER_AGENT',
    'BrowserAuthError',
    'AuthenticationError',
    'ValidationError',
    'ConfigurationError',
    'StateFileError',
]
