"""MCP Service Package

多租户任务和记忆管理服务，支持Model Context Protocol (MCP)。

主要功能：
- 任务管理：CRUD操作、批量处理、任务分解
- 记忆管理：知识存储、搜索、标签分类
- 版本控制：状态跟踪、审计日志、回滚
- 项目隔离：多租户支持、数据隔离
"""

__version__ = "1.0.0"
__author__ = "MCP Service Team"

__all__ = [
    "__version__",
    "__author__",
]