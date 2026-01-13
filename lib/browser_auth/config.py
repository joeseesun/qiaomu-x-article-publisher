# ~/.claude/skills/shared-lib/browser_auth/config.py
"""
Browser Authentication Framework - 站点配置
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable


@dataclass
class SiteConfig:
    """
    网站认证配置

    使用配置驱动的验证策略，支持多种验证方式：
    - URL 模式匹配（最快）
    - Cookie 存在性检查（快速）
    - DOM 元素检查（需等待渲染）
    - 自定义验证函数（复杂场景）
    """

    # 基础信息
    site_name: str                          # 网站标识，如 "notebooklm" | "x-twitter"
    login_url: str                          # 登录页面 URL

    # 验证策略（任一满足即认为登录成功，按优先级执行）
    success_indicators: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "url_contains": "home",                      # URL 包含关键字
    #   "url_pattern": r"^https://x\.com/home",     # URL 正则匹配
    #   "element_exists": "nav[aria-label='Primary']",  # 元素存在
    #   "cookie_exists": "auth_token"                # Cookie 存在
    # }

    # 超时配置
    login_timeout_minutes: int = 10

    # 可选：自定义验证函数（复杂场景）
    # 签名: validate_fn(page: Page) -> bool
    custom_validator: Optional[Callable] = None

    def __post_init__(self):
        """配置验证"""
        if not self.site_name:
            raise ValueError("site_name 不能为空")
        if not self.login_url:
            raise ValueError("login_url 不能为空")
        if not self.success_indicators and not self.custom_validator:
            raise ValueError("必须提供 success_indicators 或 custom_validator")


# 默认浏览器配置常量
DEFAULT_BROWSER_ARGS = [
    '--disable-blink-features=AutomationControlled',  # 隐藏 navigator.webdriver
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--no-first-run',
    '--no-default-browser-check'
]

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
