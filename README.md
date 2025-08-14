# WR124 - 多租户智能体任务管理系统

一个完整的多租户智能体任务管理系统，集成 Model Context Protocol (MCP) 服务、AI 智能体和现代化前端界面，为 AI 驱动的项目管理和开发提供完整解决方案。

## 🎯 项目概览

WR124 是一个现代化的智能体任务管理系统，由三个核心组件构成：

- **wr124/** - AI 智能体核心框架，基于 AutoGen 的先进智能体系统
- **shrimp/** - MCP（Model Context Protocol）任务管理服务，提供 REST API 和 MCP 协议支持  
- **frontend/** - React 前端应用，提供直观的任务管理界面

## ✨ 核心特性

### 🏗️ 系统架构
- **多租户隔离**：基于 `project_id` 的完整数据隔离
- **微服务架构**：前后端分离的现代化设计
- **实时同步**：前后端实时数据同步
- **事件驱动**：基于事件总线的可扩展架构

### 🤖 智能体功能
- **AutoGen 集成**：基于最先进的 AutoGen 框架
- **任务分解**：AI 驱动的复杂任务自动分解
- **智能规划**：基于上下文的任务优先级排序
- **记忆系统**：知识存储和检索增强
- **版本控制**：完整的任务变更历史追踪

### 💾 数据管理
- **MongoDB 主存储**：高效的文档数据存储
- **向量索引**：为 RAG 应用提供语义搜索
- **版本历史**：append-only 的不可变历史记录
- **乐观并发控制**：防止数据冲突

### 🔌 API 服务
- **RESTful API**：完整的 HTTP API 接口
- **MCP 协议**：原生 Model Context Protocol 支持
- **WebSocket**：实时双向通信
- **GraphQL**：可扩展的查询接口

### 🎨 前端界面
- **React 18**：现代化的响应式界面
- **Bootstrap 5**：美观的 UI 组件库
- **实时更新**：无需刷新的实时数据同步
- **移动友好**：响应式设计适配所有设备

## 📁 项目结构

```
wr124/
├── wr124/                    # AI 智能体框架
│   ├── agent_base.py        # 基础智能体类
│   ├── agent_plan.py        # 任务规划器
│   ├── filesystem/          # 文件系统工具
│   └── prompt_*.py          # 提示词模板
├── shrimp/                   # MCP 任务管理服务
│   ├── main.py              # 服务端入口
│   ├── api/                 # REST API 路由
│   ├── services/            # 业务逻辑层
│   ├── models/              # 数据模型
│   └── tools/               # MCP 工具定义
├── frontend/                 # React 前端应用
│   ├── src/App.js           # 主应用组件
│   ├── src/components/      # UI 组件库
│   └── package.json         # 前端依赖配置
├── docs/                     # 项目文档
├── tests/                    # 测试套件
├── script/                   # 启动脚本
└── README.md                # 项目说明（本文件）
```

## 🚀 快速开始

### 环境要求

```bash
Python 3.10+
Node.js 16+
MongoDB 4.4+
```

### 安装依赖

```bash
# 安装 Python 依赖
pip install -e .

# 安装前端依赖
cd frontend && npm install
```

### 启动服务

#### 方法1：使用启动脚本
```bash
# 一键启动所有服务
python script/run_server.py
```

#### 方法2：手动启动
```bash
# 启动 MongoDB 服务
mongod

# 启动 MCP 服务（端口 8000）
python -m shrimp.main

# 启动前端开发服务器（端口 3000）
cd frontend && npm start

# 启动 AI 智能体
python script/run_agent.py
```

### 访问服务

- **前端界面**：http://localhost:3000
- **API 文档**：http://localhost:8000/docs
- **MCP 端点**：http://localhost:8000/mcp
- **数据库**：mongodb://localhost:27017/wr124

## 🔧 核心组件详细说明

### WR124 - AI 智能体框架

**功能定位**：AI 驱动的智能管理助手

**核心能力**：
- 基于 AutoGen 的多智能体协调
- 任务自动化分解和规划
- 智能上下文管理和记忆
- 文件系统操作和代码审查
- 实时任务状态跟踪

**运行模式**：
```bash
# 启动智能体控制台
python wr124/agent_base.py

# 使用智能体进行任务分解
python script/run_agent.py "创建新的用户管理系统"
```

### Shrimp - MCP 任务管理服务

**功能定位**：核心的任务和数据管理服务

**服务架构**：
- `main.py` - FastAPI 和 FastMCP 集成启动器
- `api/routes/` - RESTful API 路由处理器
- `services/` - 业务逻辑层，包含任务、记忆、版本服务
- `tools/` - MCP 协议工具定义
- `models/` - Pydantic 数据模型

**核心 API**：
```
# 任务管理
GET    /api/v1/tasks           # 获取任务列表
POST   /api/v1/tasks           # 创建任务
GET    /api/v1/tasks/{id}      # 任务详情
PUT    /api/v1/tasks/{id}      # 更新任务
DELETE /api/v1/tasks/{id}      # 删除任务

# 记忆管理  
GET    /api/v1/memories        # 获取记忆列表
POST   /api/v1/memories        # 创建知识记忆
PUT    /api/v1/memories/{id}   # 更新记忆

# 版本控制
GET    /api/v1/versions/{task_id}    # 获取版本历史
POST   /api/v1/versions/{task_id}    # 创建版本快照
POST   /api/v1/versions/revert/{id}  # 版本回滚
```

### Frontend - React 前端界面

**功能定位**：现代化的管理界面

**技术栈**：
- React 18 + Hooks
- Bootstrap 5 + React-Bootstrap
- Axios 进行 HTTP 通信
- 实时状态管理

**核心组件**：
- **UnifiedTaskManager** - 统合的任务管理界面
- **TaskTableView** - 任务表格视图
- **CreateTaskModal** - 任务创建对话框
- **TaskDetailModal** - 任务详情查看器
- **TaskVersionModal** - 版本历史查看
- **ProjectSidebar** - 多项目导航

**启动和构建**：
```bash
cd frontend
npm start       # 开发模式
npm run build   # 生产构建
npm test        # 运行测试
```

## 📊 使用场景

### 1. AI 辅助项目管理
```bash
# 创建新项目并自动分解任务
python script/run_agent.py "开发新的电商网站，包含商品管理、订单系统和支付集成"
```

### 2. 多团队协作
- 每个团队拥有独立的项目空间
- 任务分配和进度跟踪
- 版本历史追踪

### 3. 知识管理
- 存储最佳实践和技术文档
- 智能搜索和相关推荐
- 版本化知识更新

### 4. 代码审查工作流
- AI 自动代码分析
- 审查任务分发
- 问题解决跟踪

## 🔐 多租户架构

### 项目隔离机制
- **数据隔离**：MongoDB 集合级隔离
- **API 路由**：基于请求头的自动路由
- **权限控制**：项目级别的权限验证

### 使用方法
```bash
# 指定项目 ID 创建任务
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "X-Project-ID: team-alpha" \
  -H "Content-Type: application/json" \
  -d '{"name": "API 开发", "description": "用户认证 API 实现"}'
```

## 🧪 测试和开发

### 测试套件
```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试  
pytest tests/integration/

# 运行压力测试
pytest tests/test_task_service_stress.py
```

### 开发工具
```bash
# 代码格式化
black wr124/ shrimp/

# 类型检查
mypy wr124/ shrimp/

# 前端代码检查
npm run lint  # 前端项目
```

## 📦 部署指南

### 生产环境部署
```bash
# 1. 构建前端
npm run build

# 2. 配置环境变量
export MONGODB_URL="mongodb://prod-server:27017/wr124"
export DEBUG=false

# 3. 使用进程管理器启动
pm2 start "python -m shrimp.main" --name mcp-server
pm2 start "python script/run_agent.py" --name agent-service
```

### Docker 部署
```yaml
# docker-compose.yml 示例
version: '3.8'
services:
  mongodb:
    image: mongo:4.4
  mcp-server:
    build: ./shrimp
  frontend:
    build: ./frontend
  agent:
    build: ./wr124
```

## 🤝 贡献指南

### 开发环境设置
1. Fork 项目仓库
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交代码： `git commit -m "Add new feature"`
4. 推送到分支： `git push origin feature/new-feature`
5. 创建 Pull Request

### 代码规范
- 遵循 PEP 8 Python 编码规范
- 使用 Type Hints 进行类型注解
- 编写单元测试覆盖新功能
- 更新相关文档

## 📄 许可证

本项目基于 MIT License 开源协议，允许商业使用和修改。

## 🙋‍♂️ 支持和联系

- **文档**：`/docs/` 目录下包含详细的技术文档
- **Issues**：GitHub Issues 进行问题报告
- **Discussion**：GitHub Discussions 进行技术讨论

---

**WR124** - 将 AI 智能体与现代项目管理完美融合，让复杂项目开发变得简单而高效。