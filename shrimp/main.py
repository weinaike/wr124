"""Main FastAPI application for MCP service."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shrimp.api.routes.router import router as api_router
from shrimp.core.config import settings
from shrimp.core.events import startup_event, shutdown_event

from contextlib import asynccontextmanager
from fastmcp import FastMCP
from shrimp.db.database import mcp_db_manager
from shrimp.tools import (
    register_task_tools,
    register_memory_tools,
    register_todo_tools
)

# 1. Define Lifespan manager for database connection
@asynccontextmanager
async def lifespan(app: FastMCP):
    """
    Context manager to handle server startup and shutdown events.
    Connects to the database on startup and disconnects on shutdown.
    """
    print("Connecting to MCP database...")
    await mcp_db_manager.connect_to_mongo()
    yield
    print("Disconnecting from MCP database...")
    await mcp_db_manager.close_mongo_connection()


# 2. Create the FastMCP Application with the lifespan manager
mcp = FastMCP(
    name="MultiProjectMCPServer",
    lifespan=lifespan,
)

# 3. Register all tool modules
# 注册任务管理工具 - 提供完整的任务CRUD、批量操作、状态管理功能
register_task_tools(mcp)

# 注册记忆管理工具 - 提供知识存储、搜索、标签分类、向量索引功能
register_memory_tools(mcp)
# 注册待办事项管理工具 - 提供任务的代办事项管理功能
register_todo_tools(mcp)
# Create ASGI app from MCP server
mcp_app = mcp.http_app(path='/mcp')


def create_application() -> FastAPI:
    """Create FastAPI application instance."""
    app = FastAPI(
        lifespan=mcp_app.lifespan,
        title="MCP Service",
        description="Model Context Protocol Service Implementation",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add event handlers
    app.add_event_handler("startup", startup_event)
    app.add_event_handler("shutdown", shutdown_event)

    # Add routes
    app.include_router(api_router)

    return app

app = create_application()

app.mount("/", mcp_app)

if __name__ == "__main__":

    uvicorn.run(
        "shrimp.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
