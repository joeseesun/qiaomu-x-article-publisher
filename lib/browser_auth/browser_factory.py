# ~/.claude/skills/shared-lib/browser_auth/browser_factory.py
"""
Browser Authentication Framework - 浏览器工厂
负责创建配置好的浏览器上下文，处理 Playwright session cookie bug
"""

import json
from pathlib import Path
from typing import Optional

from patchright.sync_api import Playwright, BrowserContext

from .config import DEFAULT_BROWSER_ARGS, DEFAULT_USER_AGENT


class BrowserFactory:
    """
    浏览器实例工厂

    核心功能：
    1. 创建 persistent context with user_data_dir（保证浏览器指纹一致性）
    2. 手动注入 state.json 中的 cookies（解决 Playwright session cookie bug）

    参考：https://github.com/microsoft/playwright/issues/36139
    """

    @staticmethod
    def launch_persistent_context(
        playwright: Playwright,
        user_data_dir: Path,
        state_file: Optional[Path] = None,
        headless: bool = True,
        user_agent: str = DEFAULT_USER_AGENT,
        browser_args: list = None
    ) -> BrowserContext:
        """
        启动持久化浏览器上下文

        Args:
            playwright: Playwright 实例
            user_data_dir: 浏览器 profile 目录
            state_file: state.json 文件路径（用于手动注入 cookies）
            headless: 是否无头模式
            user_agent: 自定义 User-Agent
            browser_args: 额外的浏览器启动参数

        Returns:
            配置好的 BrowserContext
        """
        if browser_args is None:
            browser_args = DEFAULT_BROWSER_ARGS + [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]

        # 确保目录存在
        user_data_dir.mkdir(parents=True, exist_ok=True)

        # 启动 persistent context
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            channel="chrome",  # 使用真实 Chrome，提高信任度
            headless=headless,
            no_viewport=True,
            ignore_default_args=["--enable-automation"],
            user_agent=user_agent,
            args=browser_args
        )

        # Cookie 手动注入（Playwright bug workaround）
        # Session cookies (expires=-1) 不会自动持久化到 user_data_dir
        if state_file and state_file.exists():
            BrowserFactory._inject_cookies(context, state_file)

        return context

    @staticmethod
    def _inject_cookies(context: BrowserContext, state_file: Path):
        """
        从 state.json 手动注入 cookies

        这是解决 Playwright #36139 bug 的关键步骤：
        - Persistent cookies 会自动保存到 user_data_dir
        - Session cookies 必须手动注入
        """
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                if 'cookies' in state and len(state['cookies']) > 0:
                    context.add_cookies(state['cookies'])
                    # print(f"  🔧 注入 {len(state['cookies'])} cookies")
        except Exception as e:
            # 非致命错误，首次 setup 时 state.json 不存在
            pass
