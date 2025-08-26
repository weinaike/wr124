"""
会话管理模块
提供会话状态管理、持久化和恢复功能
"""

from .session_state_manager import SessionStateManager, SessionStateStatus

__all__ = [
    'SessionStateManager',
    'SessionStateStatus',
]

__version__ = '1.0.0'
