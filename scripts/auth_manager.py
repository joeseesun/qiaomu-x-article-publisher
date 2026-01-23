#!/usr/bin/env python3
"""
==============================================================================
X (Twitter) Article Publisher - Authentication Manager
==============================================================================

PURPOSE:
  消除 X Article Publisher 每次执行都需要手动登录的痛点
  使用共享浏览器认证框架实现持久化登录（7天有效期）

ARCHITECTURE:
  Thin wrapper around shared-lib/browser_auth framework
  Enables passwordless workflow for X article publishing

CLI INTERFACE:
  - setup [--headless] [--timeout N]  : 首次登录设置
  - status                             : 检查认证状态
  - validate                           : 验证认证有效性
  - clear                              : 清除认证数据
  - reauth [--timeout N]               : 重新认证 (clear + setup)

USAGE FLOW:
  1. First time: `python auth_manager.py setup`
  2. Auto-login: skill 自动使用已保存的认证状态
  3. Refresh: `python auth_manager.py reauth` (if expired)
"""

import sys
import argparse
from pathlib import Path

# ============================================================================
# PATH CONFIGURATION - 使用skill内部的browser_auth库
# ============================================================================
SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "lib"))
sys.path.insert(0, str(Path(__file__).parent))

from browser_auth import BrowserAuthManager
from site_config import X_TWITTER_CONFIG

# ============================================================================
# PATH CONSTANTS
# ============================================================================
DATA_DIR = SKILL_DIR / "data"
BROWSER_STATE_DIR = DATA_DIR / "browser_state"


# ============================================================================
# X AUTHENTICATION MANAGER
# ============================================================================
class XAuthManager:
    """
    X (Twitter) 认证管理器

    DESIGN:
      Delegates all core logic to BrowserAuthManager
      Provides X-specific CLI and error messages

    CORE METHODS:
      - is_authenticated() -> bool
      - get_auth_info() -> Dict
      - setup_auth(headless, timeout_minutes) -> bool
      - validate_auth() -> bool
      - clear_auth() -> bool
      - get_authenticated_context() -> BrowserContext
    """

    def __init__(self):
        """初始化认证管理器，委托给共享框架"""
        self.manager = BrowserAuthManager(
            site_config=X_TWITTER_CONFIG,
            state_dir=BROWSER_STATE_DIR
        )

        # 便捷访问属性
        self.state_file = self.manager.state_file
        self.auth_info_file = self.manager.auth_info_file
        self.browser_state_dir = self.manager.state_dir

    def is_authenticated(self) -> bool:
        """检查是否已认证（委托到共享框架）"""
        return self.manager.is_authenticated()

    def get_auth_info(self):
        """获取认证信息（委托到共享框架）"""
        return self.manager.get_auth_info()

    def setup_auth(self, headless: bool = False, timeout_minutes: int = 10) -> bool:
        """
        交互式登录设置

        Args:
            headless: 是否无头模式（登录时应为 False）
            timeout_minutes: 超时时间（分钟）

        Returns:
            True 如果认证成功
        """
        self.manager.config.login_timeout_minutes = timeout_minutes
        return self.manager.setup_auth(headless=headless)

    def validate_auth(self) -> bool:
        """验证现有认证（委托到共享框架）"""
        return self.manager.validate_auth()

    def clear_auth(self) -> bool:
        """清除认证数据（委托到共享框架）"""
        return self.manager.clear_auth()

    def get_authenticated_context(self):
        """获取已认证的浏览器上下文（供 skill 使用）"""
        return self.manager.get_authenticated_context()


# ============================================================================
# CLI INTERFACE
# ============================================================================
def main():
    """CLI 入口点"""
    parser = argparse.ArgumentParser(
        description='X (Twitter) Authentication Manager for Article Publisher'
    )

    # 子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # setup 命令
    setup_parser = subparsers.add_parser('setup', help='Setup authentication')
    setup_parser.add_argument('--headless', action='store_true',
                            help='Run in headless mode')
    setup_parser.add_argument('--timeout', type=float, default=10,
                            help='Login timeout in minutes (default: 10)')

    # status 命令
    subparsers.add_parser('status', help='Check authentication status')

    # validate 命令
    subparsers.add_parser('validate', help='Validate authentication')

    # clear 命令
    subparsers.add_parser('clear', help='Clear authentication')

    # reauth 命令 (clear + setup)
    reauth_parser = subparsers.add_parser('reauth',
                                         help='Re-authenticate (clear + setup)')
    reauth_parser.add_argument('--timeout', type=float, default=10,
                             help='Login timeout in minutes (default: 10)')

    args = parser.parse_args()
    auth = XAuthManager()

    # ========================================================================
    # COMMAND HANDLERS
    # ========================================================================

    if args.command == 'setup':
        print("\n" + "="*70)
        print("  X (Twitter) Authentication Setup")
        print("="*70)
        print("\nPrerequisites:")
        print("  - X Premium+ subscription (required for Articles)")
        print("  - X account credentials ready")
        print()
        print("Instructions:")
        print("  1. Browser window will open to X login page")
        print("  2. Sign in with your X account")
        print("  3. Complete 2FA if enabled")
        print("  4. Wait for redirect to Home timeline")
        print("  5. Authentication will be saved automatically")
        print()
        print("Timeout: {} minutes\n".format(int(args.timeout)))

        success = auth.setup_auth(
            headless=args.headless,
            timeout_minutes=int(args.timeout)
        )

        if success:
            print("\n" + "="*70)
            print("  Authentication setup complete!")
            print("="*70)
            print("\n  You can now publish articles without logging in!")
            print("  Authentication valid for 7 days\n")
        else:
            print("\n" + "="*70)
            print("  Authentication setup failed")
            print("="*70)
            print("\n  Troubleshooting:")
            print("    - Ensure you completed login within timeout")
            print("    - Check your X credentials")
            print("    - Verify Premium+ subscription is active\n")

        sys.exit(0 if success else 1)

    elif args.command == 'status':
        info = auth.get_auth_info()
        print("\n" + "="*70)
        print("  X (Twitter) Authentication Status")
        print("="*70)
        for key, value in info.items():
            print(f"  {key}: {value}")
        print("="*70 + "\n")
        sys.exit(0 if info['authenticated'] else 1)

    elif args.command == 'validate':
        print("\nValidating X authentication...")
        is_valid = auth.validate_auth()

        if is_valid:
            print("\nAuthentication is valid")
            print("  You can publish articles now!\n")
        else:
            print("\nAuthentication is invalid")
            print("  Please run: python auth_manager.py setup\n")

        sys.exit(0 if is_valid else 1)

    elif args.command == 'clear':
        print("\nClearing X authentication data...")
        success = auth.clear_auth()

        if success:
            print("\nAuthentication data cleared")
            print("  Run 'setup' to re-authenticate\n")
        else:
            print("\nFailed to clear authentication data\n")

        sys.exit(0 if success else 1)

    elif args.command == 'reauth':
        print("\nRe-authenticating X account...")

        # Step 1: Clear existing auth
        print("\n  Step 1/2: Clearing old authentication...")
        auth.clear_auth()

        # Step 2: Setup new auth
        print("\n  Step 2/2: Setting up new authentication...")
        print("  Browser will open shortly...\n")
        success = auth.setup_auth(timeout_minutes=int(args.timeout))

        if success:
            print("\nRe-authentication complete!")
            print("  Ready to publish articles\n")
        else:
            print("\nRe-authentication failed")
            print("  Please try again or check credentials\n")

        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
