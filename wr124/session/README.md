# 会话状态管理模块

WR124 项目的模块化会话状态管理系统，提供完整的会话状态持久化、查询和恢复功能。

## 🎯 设计目标

- **模块化**：独立的会话状态管理模块，可单独使用或集成
- **灵活性**：支持多种HTTP客户端和配置方式
- **容错性**：网络错误不影响主要功能
- **易用性**：简单的API设计和自动化集成

## 📦 模块结构

```
wr124/session/
├── __init__.py                    # 模块导出
└── session_state_manager.py      # 核心会话状态管理器
```

## 🚀 核心功能

### SessionStateManager

独立的会话状态管理器，提供完整的状态管理功能：

```python
from wr124.session import SessionStateManager, SessionStateStatus

# 创建管理器
manager = SessionStateManager("session_123")

# 上传状态
status, doc_id = await manager.upload_session_state(
    state={"key": "value"},
    task="任务描述",
    agent_name="agent_name"
)

# 下载历史
status, states = await manager.download_session_states(limit=10)

# 恢复状态
status, data = await manager.restore_session_state(doc_id)

# 删除状态  
status, msg = await manager.delete_session_state(doc_id)
```

### Team类集成

通过组合模式，Team类自动集成会话状态管理：

```python
from wr124.agents.team_base import Team

# Team自动创建并管理SessionStateManager
team = Team(model_client, session_id="team_session")

# 执行任务时自动上传状态
async for msg in team.execute_task("task"):
    pass

# 使用便利方法
status, history = await team.download_session_history()
```

## ⚙️ 环境配置

```bash
# 启用会话状态管理
export ENABLE_SESSION_STATE_UPLOAD=true

# API服务地址
export SESSION_API_URL=http://localhost:8000

# 项目ID
export DEFAULT_PROJECT_ID=default

# 超时设置（可选，默认10秒）
export SESSION_STATE_TIMEOUT=10
```

## 📊 状态枚举

```python
from wr124.session import SessionStateStatus

# 可能的状态值
SessionStateStatus.SUCCESS     # 操作成功
SessionStateStatus.FAILED      # 操作失败  
SessionStateStatus.DISABLED    # 功能禁用
SessionStateStatus.TIMEOUT     # 请求超时
SessionStateStatus.NO_CLIENT   # 缺少HTTP客户端
```

## 🔧 依赖管理

模块自动处理HTTP客户端依赖：

1. **优先级1**: `aiohttp` - 推荐的异步HTTP客户端
2. **优先级2**: `httpx` - 备选异步HTTP客户端  
3. **优先级3**: `urllib` - 内置同步HTTP客户端

```bash
# 推荐安装
pip install aiohttp

# 或者
pip install httpx
```

## 📝 数据格式

上传的JSON文档结构：

```json
{
  "name": "session_state_{session_id}_{timestamp}",
  "description": "智能体会话状态描述",
  "document_type": "user_data",
  "content": {
    "agent_name": "agent_name",
    "task": "任务内容", 
    "state": "状态数据",
    "timestamp": "2025-08-26T10:30:00",
    "tools_count": 5,
    "session_metadata": {
      "agent_description": "智能体描述",
      "agent_color": "颜色"
    }
  },
  "session_id": "session_id",
  "tags": ["session_state", "agent_state", "agent_name"],
  "metadata": {
    "upload_timestamp": "上传时间",
    "task_length": 123,
    "state_size": 456
  },
  "is_public": false
}
```

## 🧪 测试和示例

- **单元测试**: `tests/test_modular_session_state.py`
- **使用示例**: `examples/session_state_usage_example.py`
- **文档**: `docs/session_state_upload_guide.md`

## 🔄 版本历史

- **v1.0.0**: 初始版本，模块化设计
- 支持完整的CRUD操作
- 多HTTP客户端支持
- Team类无缝集成

## 📄 许可证

MIT License - 详见项目根目录的LICENSE文件
