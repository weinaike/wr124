# Shrimp Service Docker Deployment

基于 MongoDB 的 Shrimp 服务与前端页面的 Docker 部署方案。

## 🏗️ 架构

本部署方案包含以下组件：

- **MongoDB 7.0**: 数据库服务
- **Shrimp API**: FastAPI 后端服务 (端口 4444)
- **Frontend**: React 前端应用
- **Nginx**: 反向代理和静态文件服务 (端口 80)

## 🚀 快速开始

### 1. 准备环境

确保已安装：
- Docker
- Docker Compose

### 2. 配置环境变量

```bash
# 复制环境配置文件
cp .env.example .env

```

### 3. 启动服务

使用便捷的部署脚本：

```bash
# 构建并启动所有服务
./deploy.sh up

# 或者使用 docker-compose
docker-compose up -d
```

### 4. 访问服务

- **前端页面**: http://localhost:80
- **API 文档**: http://localhost:4444/docs
- **MongoDB**: localhost:27017

## 🛠️ 管理命令

```bash
# 构建镜像
./deploy.sh build

# 启动服务
./deploy.sh up

# 停止服务
./deploy.sh down

# 重启服务
./deploy.sh restart

# 查看日志
./deploy.sh logs

# 查看状态
./deploy.sh status
```

## 📁 文件结构

```
.
├── Dockerfile              # 应用容器构建文件
├── docker-compose.yml      # 服务编排配置
├── deploy.sh               # 部署管理脚本
├── .env.example            # 环境变量示例
├── .dockerignore           # Docker 构建忽略文件
└── docker/
    └── mongo-init/
        └── init-mcp-db.js  # MongoDB 初始化脚本
```

## 🔧 自定义配置

### MongoDB 配置

默认 MongoDB 配置：(不校验)
- 用户名: `admin`
- 密码: `password`
- 数据库: `mcp_db`

可以在 `.env` 文件中修改这些配置。

### 端口配置

- **80**: Nginx (前端 + API 代理)
- **4444**: Shrimp API 直接访问
- **27017**: MongoDB

### 数据持久化

MongoDB 数据存储在 Docker volume `mongodb_data` 中，确保数据持久化。

## 🐛 故障排除

### 查看服务状态

```bash
docker-compose ps
```

### 查看特定服务日志

```bash
# 查看 MongoDB 日志
docker-compose logs mongodb

# 查看应用日志
docker-compose logs shrimp-app
```

### 重置数据库

```bash
# 停止服务
./deploy.sh down

# 删除数据卷
docker volume rm wr124_mongodb_data

# 重新启动
./deploy.sh up
```

### 进入容器调试

```bash
# 进入应用容器
docker-compose exec shrimp-app bash

# 进入 MongoDB 容器
docker-compose exec mongodb mongosh
```

## 🔒 安全注意事项

1. **更改默认密码**: 在生产环境中，务必修改 `.env` 文件中的默认密码
2. **SECRET_KEY**: 使用强随机字符串作为 SECRET_KEY
3. **网络安全**: 根据需要调整端口暴露和防火墙规则
4. **SSL/TLS**: 在生产环境中配置 HTTPS

## 📊 监控和日志

- 日志文件存储在 `./logs` 目录中
- 健康检查已配置，可通过 `docker-compose ps` 查看状态
- 使用 `./deploy.sh status` 快速检查服务健康状态

## 🚀 生产环境部署

生产环境建议：

1. 使用专用的 MongoDB 集群
2. 配置 SSL/TLS 证书
3. 设置适当的资源限制
4. 配置日志轮转
5. 设置监控和告警
6. 定期备份数据库

## 📝 开发模式

如需开发模式，可以：

```bash
# 设置开发环境变量
echo "DEBUG=true" >> .env

# 重启服务
./deploy.sh restart
```
