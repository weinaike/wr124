"""Database connection and utilities for Motor."""

from typing import Optional, Protocol, cast
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
import logging

from shrimp.core.config import settings

logger = logging.getLogger(__name__)


class MCPDatabase(Protocol):
    """Structural typing for project collections on top of Motor database.

    This provides explicit attribute types for collections like db.tasks so that
    editors and type checkers can recognize them when calling create_index, etc.
    """

    tasks: AsyncIOMotorCollection
    task_versions: AsyncIOMotorCollection
    memories: AsyncIOMotorCollection
    embeddings: AsyncIOMotorCollection
    audit_logs: AsyncIOMotorCollection


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self):
        """Initialize with instance variables for connection isolation."""
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
    
    async def connect_to_mongo(self):
        """Connect to MongoDB."""
        logger.info(f"Connecting to MongoDB at {settings.MONGO_URI}")
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self.database = self.client[settings.DATABASE_NAME]
        
        # Test connection
        try:
            await self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise
    
    async def close_mongo_connection(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database
    
    async def get_async_connection(self) -> AsyncIOMotorDatabase:
        """Get database connection with auto-connect (for API routes)."""
        if self.database is None:
            await self.connect_to_mongo()
        return self.database


# Global database manager instances
db_manager = DatabaseManager()
mcp_db_manager = DatabaseManager()


async def connect_to_mongo():
    """Connect to MongoDB (wrapper for FastAPI events)."""
    await db_manager.connect_to_mongo()


async def close_mongo_connection():
    """Close MongoDB connection (wrapper for FastAPI events).""" 
    await db_manager.close_mongo_connection()


def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    return db_manager.get_database()


async def get_async_database() -> AsyncIOMotorDatabase:
    """Get database with auto-connect (for FastAPI routes)."""
    if db_manager.database is None:
        await db_manager.connect_to_mongo()
    return db_manager.database


async def init_collections():
    """Initialize collections with indexes."""
    db = cast(MCPDatabase, get_database())
    
    # Create indexes for tasks
    await db.tasks.create_index([("project_id", 1), ("status", 1)])
    await db.tasks.create_index([("project_id", 1), ("name", 1)])
    await db.tasks.create_index([("project_id", 1), ("current_version_id", 1)])
    
    # Create indexes for task_versions
    await db.task_versions.create_index([("task_id", 1), ("timestamp", -1)])
    await db.task_versions.create_index([("project_id", 1), ("task_id", 1)])
    
    # Create indexes for memories
    await db.memories.create_index([("raw_text", "text"), ("title", "text")], name="memories_text_index")
    await db.memories.create_index([("project_id", 1), ("task_id", 1)])
    await db.memories.create_index([("project_id", 1), ("tags", 1)])
    
    # Create indexes for embeddings
    await db.embeddings.create_index([("project_id", 1), ("origin_type", 1)])
    await db.embeddings.create_index([("project_id", 1), ("origin_id", 1)])
    
    # Create indexes for audit_logs
    await db.audit_logs.create_index([("project_id", 1), ("timestamp", -1)])
    await db.audit_logs.create_index([("project_id", 1), ("user", 1)])
    await db.audit_logs.create_index([("project_id", 1), ("action", 1)])
    
    logger.info("Database collections and indexes initialized")