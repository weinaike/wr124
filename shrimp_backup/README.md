# Shrimp - MCP Service

一个基于 Model Context Protocol (MCP) 的任务和记忆管理服务，提供完整的项目管理、知识管理和版本控制能力。

## 特性

- **多租户隔离**：基于 `project_id` 的严格数据隔离
- **任务管理**：完整的任务 CRUD、批量操作、状态管理功能
- **记忆管理**：知识存储、搜索、标签分类、向量索引支持
- **版本控制**：完整的版本历史记录和回滚功能
- **REST API**：完整的 HTTP REST API 接口
- **MCP 协议**：原生支持 Model Context Protocol
- **MongoDB**：使用 MongoDB 作为主数据存储
- **乐观锁**：并发操作支持

## 快速开始

### 安装依赖

```bash
pip install -e .
```

### 运行服务

```bash
python -m shrimp.main
```

服务将在 `http://localhost:8000` 启动。

- API 文档：`http://localhost:8000/docs`
- ReDoc 文档：`http://localhost:8000/redoc`
- MCP 端点：`http://localhost:8000/mcp`

## 项目结构

```
shrimp/
├── __init__.py
├── main.py              # 应用程序入口点
├── api/                 # REST API 路由
│   ├── dependencies.py  # API 依赖项
│   ├── routes/         # 路由定义
│   └── utils.py         # API 工具函数
├── core/                # 核心配置和事件
│   ├── config.py        # 应用配置
│   ├── events.py        # 事件处理器
│   ├── response.py      # 响应格式
│   └── validators.py    # 验证器
├── db/                  # 数据库相关
│   ├── database.py      # MongoDB 连接管理
│   └── schema_generator.py # 模式生成器
├── models/              # Pydantic 数据模型
│   ├── base.py          # 基础模型
│   ├── task.py          # 任务模型
│   ├── memory.py        # 记忆模型
│   ├── version.py       # 版本模型
│   └── audit.py         # 审计模型
├── services/            # 业务逻辑服务
│   ├── task_service.py  # 任务服务
│   ├── memory_service.py # 记忆服务
│   └── version_service.py # 版本服务
└── tools/               # MCP 工具定义
    ├── base_tool.py     # 工具基类
    ├── task_tools.py    # 任务管理工具
    ├── memory_tools.py  # 记忆管理工具
    ├── todo_tools.py    # 待办事项工具
    └── response_format.py # 响应格式化
```

## 核心功能

### 任务管理

提供完整的任务生命周期管理：

- **创建任务**：支持依赖关系、文件关联、实现指导等
- **任务列表**：支持状态过滤、分页查询
- **任务更新**：乐观锁保护的并发更新
- **批量操作**：批量创建、任务分解
- **状态管理**：pending、in_progress、completed 状态流转

### 记忆管理

支持知识存储和检索：

- **知识存储**：Markdown 格式内容，支持标签分类
- **语义搜索**：支持文本搜索和标签过滤
- **向量索引**：为 RAG 应用提供向量检索
- **验证机制**：知识内容验证和元数据管理

### 版本控制

完整的版本历史管理：

- **自动版本化**：每次变更自动创建版本快照
- **历史查询**：查看完整的变更历史
- **版本回滚**：支持回滚到任意历史版本
- **审计日志**：详细的操作记录和变更追踪

## API 接口

### REST API 端点

```
GET    /health                    # 健康检查
GET    /api/v1/tasks              # 获取任务列表
POST   /api/v1/tasks              # 创建任务
GET    /api/v1/tasks/{task_id}    # 获取任务详情
PUT    /api/v1/tasks/{task_id}    # 更新任务
DELETE /api/v1/tasks/{task_id}    # 删除任务

GET    /api/v1/memories           # 获取记忆列表
POST   /api/v1/memories           # 创建记忆
GET    /api/v1/memories/{memory_id} # 获取记忆详情
PUT    /api/v1/memories/{memory_id} # 更新记忆
DELETE /api/v1/memories/{memory_id} # 删除记忆

GET    /api/v1/versions/{task_id} # 获取任务版本历史
POST   /api/v1/versions/{task_id} # 创建版本快照
POST   /api/v1/versions/{task_id}/revert/{version_id} # 版本回滚
```

### MCP 协议

服务同时支持 MCP 协议，可以通过 `/mcp` 端点访问。详细的工具接口说明请参考 [tools/README.md](tools/README.md)。

## 多租户支持

所有操作都支持多租户隔离：

- **项目识别**：通过 HTTP 请求头 `X-Project-ID` 识别项目
- **数据隔离**：不同项目的数据完全隔离
- **默认项目**：未指定 project_id 时使用 'default' 项目

### 使用示例

```bash
# 指定项目 ID
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -H "X-Project-ID: my-project" \
  -d '{"name": "新任务", "description": "任务描述"}'
```

## 配置

环境变量配置：

```bash
# 数据库配置
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DB_NAME=shrimp

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=true

# CORS 配置
ALLOWED_HOSTS=["http://localhost:3000", "http://127.0.0.1:3000"]
```

## 开发

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
pytest -m unit          # 仅运行单元测试
pytest -m integration   # 仅运行集成测试
```

### 代码格式化

```bash
black shrimp/
```

### 类型检查

```bash
mypy shrimp/
```

## 依赖项

### 核心依赖

- **FastAPI**：现代 Web 框架
- **Motor**：异步 MongoDB 驱动
- **Pydantic**：数据验证和序列化
- **FastMCP**：Model Context Protocol 支持
- **Uvicorn**：ASGI 服务器

### 认证依赖

- **python-jose**：JWT 处理
- **passlib**：密码哈希
- **bcrypt**：密码加密

### 开发依赖

- **pytest**：测试框架
- **black**：代码格式化
- **mypy**：类型检查
- **httpx**：HTTP 客户端

## 许可证

MIT License