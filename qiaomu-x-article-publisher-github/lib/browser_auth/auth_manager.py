# ~/.claude/skills/shared-lib/browser_auth/auth_manager.py
"""
Browser Authentication Framework - 核心认证管理器
"""

import json
import time
import re
from pathlib import Path
from typing import Dict, Any

from patchright.sync_api import sync_playwright, BrowserContext, Page

from .config import SiteConfig
from .browser_factory import BrowserFactory
from .exceptions import AuthenticationError, ValidationError, StateFileError


class BrowserAuthManager:
    """
    通用浏览器认证管理器

    核心功能：
    1. 交互式登录设置（setup_auth）
    2. 认证状态检查（is_authenticated）
    3. 认证验证（validate_auth）
    4. 获取已认证上下文（get_authenticated_context）
    5. 清除认证（clear_auth）

    混合认证方案：
    - user_data_dir: 保证浏览器指纹一致性
    - state.json: 手动注入 session cookies
    """

    def __init__(self, site_config: SiteConfig, state_dir: Path):
        """
        初始化认证管理器

        Args:
            site_config: 网站配置
            state_dir: 状态存储目录（如 ~/.claude/skills/x-publisher/data/browser_state）
        """
        self.config = site_config
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "state.json"
        self.profile_dir = self.state_dir / "browser_profile"
        self.auth_info_file = self.state_dir.parent / "auth_info.json"

        # 确保目录存在
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def is_authenticated(self) -> bool:
        """
        快速检查认证状态（不启动浏览器）

        检查 state.json 是否存在且未过期（7天）

        Returns:
            True 如果已认证
        """
        if not self.state_file.exists():
            return False

        # 检查文件年龄（7天过期）
        age_days = (time.time() - self.state_file.stat().st_mtime) / 86400
        if age_days > 7:
            print(f"⚠️  Browser state is {age_days:.1f} days old, may need re-authentication")

        return True

    def get_auth_info(self) -> Dict[str, Any]:
        """
        获取认证信息元数据

        Returns:
            包含认证状态和时间戳的字典
        """
        info = {
            'site_name': self.config.site_name,
            'authenticated': self.is_authenticated(),
            'state_file': str(self.state_file),
            'state_exists': self.state_file.exists()
        }

        if self.auth_info_file.exists():
            try:
                with open(self.auth_info_file, 'r') as f:
                    saved_info = json.load(f)
                    info.update(saved_info)
            except Exception:
                pass

        if info['state_exists']:
            age_hours = (time.time() - self.state_file.stat().st_mtime) / 3600
            info['state_age_hours'] = age_hours

        return info

    def _check_success_indicators(self, page: Page) -> bool:
        """
        根据 success_indicators 配置检查登录是否成功

        验证优先级：
        1. URL 检查（最快）
        2. Cookie 检查（快速）
        3. DOM 元素检查（需等待）
        4. 自定义验证函数（可选）

        Args:
            page: Playwright Page 实例

        Returns:
            True 如果验证成功
        """
        indicators = self.config.success_indicators

        # 1. URL 包含检查
        if 'url_contains' in indicators:
            if indicators['url_contains'] in page.url:
                return True

        # 2. URL 正则匹配
        if 'url_pattern' in indicators:
            if re.match(indicators['url_pattern'], page.url):
                return True

        # 3. Cookie 存在性检查
        if 'cookie_exists' in indicators:
            cookies = page.context.cookies()
            cookie_names = [c['name'] for c in cookies]
            if indicators['cookie_exists'] in cookie_names:
                return True

        # 4. DOM 元素存在性检查
        if 'element_exists' in indicators:
            try:
                selector = indicators['element_exists']
                # 等待最多 5 秒
                element = page.wait_for_selector(selector, timeout=5000)
                if element:
                    return True
            except Exception:
                pass

        # 5. 自定义验证函数
        if self.config.custom_validator:
            try:
                return self.config.custom_validator(page)
            except Exception as e:
                print(f"  ⚠️  Custom validator error: {e}")

        return False

    def setup_auth(self, headless: bool = False) -> bool:
        """
        交互式登录设置

        工作流程：
        1. 启动 persistent context with user_data_dir
        2. 导航到 login_url
        3. 等待用户手动登录
        4. 根据 success_indicators 验证登录成功
        5. 保存 state.json + browser_profile

        Args:
            headless: 是否无头模式（登录时应为 False）

        Returns:
            True 如果认证成功
        """
        print(f"🔐 Starting authentication setup for {self.config.site_name}...")
        print(f"  Timeout: {self.config.login_timeout_minutes} minutes")

        playwright = None
        context = None

        try:
            playwright = sync_playwright().start()

            # 启动 persistent context
            context = BrowserFactory.launch_persistent_context(
                playwright,
                user_data_dir=self.profile_dir,
                state_file=self.state_file,
                headless=headless
            )

            # 导航到登录页面
            page = context.new_page()
            page.goto(self.config.login_url, wait_until="domcontentloaded")

            # 检查是否已经登录
            if self._check_success_indicators(page):
                print("  ✅ Already authenticated!")
                self._save_browser_state(context)
                return True

            # 等待手动登录
            print(f"\n  ⏳ Please log in to {self.config.site_name}...")
            print(f"  ⏱️  Waiting up to {self.config.login_timeout_minutes} minutes for login...")

            # 轮询检查登录状态
            timeout_seconds = self.config.login_timeout_minutes * 60
            start_time = time.time()

            while time.time() - start_time < timeout_seconds:
                if self._check_success_indicators(page):
                    print(f"  ✅ Login successful!")
                    self._save_browser_state(context)
                    self._save_auth_info()
                    return True

                time.sleep(2)  # 每 2 秒检查一次

            print(f"  ❌ Authentication timeout")
            return False

        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False

        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            if playwright:
                try:
                    playwright.stop()
                except Exception:
                    pass

    def _save_browser_state(self, context: BrowserContext):
        """保存浏览器状态到 state.json"""
        try:
            context.storage_state(path=str(self.state_file))
            print(f"  💾 Saved browser state to: {self.state_file}")
        except Exception as e:
            raise StateFileError(f"Failed to save browser state: {e}")

    def _save_auth_info(self):
        """保存认证元数据"""
        try:
            info = {
                'site_name': self.config.site_name,
                'authenticated_at': time.time(),
                'authenticated_at_iso': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.auth_info_file, 'w') as f:
                json.dump(info, f, indent=2)
        except Exception:
            pass  # 非关键错误

    def validate_auth(self) -> bool:
        """
        验证现有认证是否有效（启动浏览器测试）

        Returns:
            True 如果认证有效
        """
        if not self.is_authenticated():
            return False

        print(f"🔍 Validating authentication for {self.config.site_name}...")

        playwright = None
        context = None

        try:
            playwright = sync_playwright().start()

            # 启动 persistent context + 注入 cookies
            context = BrowserFactory.launch_persistent_context(
                playwright,
                user_data_dir=self.profile_dir,
                state_file=self.state_file,
                headless=True
            )

            # 访问登录后的页面进行验证
            page = context.new_page()
            page.goto(self.config.login_url, wait_until="domcontentloaded")

            # 检查验证指标
            is_valid = self._check_success_indicators(page)

            if is_valid:
                print("  ✅ Authentication is valid")
            else:
                print("  ❌ Authentication is invalid")

            return is_valid

        except Exception as e:
            print(f"  ❌ Validation error: {e}")
            return False

        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            if playwright:
                try:
                    playwright.stop()
                except Exception:
                    pass

    def get_authenticated_context(self) -> BrowserContext:
        """
        获取已认证的浏览器上下文（供 skill 使用）

        工作流程：
        1. 检查 is_authenticated()
        2. 启动 persistent context
        3. 手动注入 cookies from state.json
        4. 返回 context（调用者负责关闭）

        Returns:
            已认证的 BrowserContext

        Raises:
            AuthenticationError: 如果未认证
        """
        if not self.is_authenticated():
            raise AuthenticationError(
                f"Not authenticated for {self.config.site_name}. "
                f"Please run setup_auth() first."
            )

        playwright = sync_playwright().start()

        context = BrowserFactory.launch_persistent_context(
            playwright,
            user_data_dir=self.profile_dir,
            state_file=self.state_file,
            headless=True
        )

        return context

    def clear_auth(self):
        """
        清除所有认证数据

        删除：
        - state.json（session cookies）
        - browser_profile（persistent cookies + 浏览器指纹）
        - auth_info.json（认证元数据）
        """
        print(f"🧹 Clearing authentication data for {self.config.site_name}...")

        # 删除 state.json
        if self.state_file.exists():
            self.state_file.unlink()
            print(f"  ✓ Removed {self.state_file}")

        # 删除 browser profile 目录
        if self.profile_dir.exists():
            import shutil
            shutil.rmtree(self.profile_dir)
            print(f"  ✓ Removed {self.profile_dir}")

        # 删除 auth_info.json
        if self.auth_info_file.exists():
            self.auth_info_file.unlink()
            print(f"  ✓ Removed {self.auth_info_file}")

        print("  ✅ Authentication cleared")
