"""
Browser Authentication Framework - 异常定义
"""


class BrowserAuthError(Exception):
    """浏览器认证基础异常"""
    pass


class AuthenticationError(BrowserAuthError):
    """认证失败异常"""
    pass


class ValidationError(BrowserAuthError):
    """验证失败异常"""
    pass


class ConfigurationError(BrowserAuthError):
    """配置错误异常"""
    pass


class StateFileError(BrowserAuthError):
    """状态文件错误异常"""
    pass
