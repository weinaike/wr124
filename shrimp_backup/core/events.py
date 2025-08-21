"""Application startup and shutdown events."""

import logging
from typing import Any

from fastapi import FastAPI

from shrimp.core.config import settings
from shrimp.db.database import close_mongo_connection, connect_to_mongo, init_collections

logger = logging.getLogger(__name__)


async def startup_event(app: FastAPI) -> None:
    """Application startup event."""
    logger.info("Starting MCP Service...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    logger.info("Connected to MongoDB")
    
    # Initialize collections and indexes
    await init_collections()
    logger.info("Database collections initialized")
    
    # Log configuration
    logger.info(f"Running MCP service on {settings.HOST}:{settings.PORT}")
    logger.info(f"MongoDB: {settings.MONGO_URI}")
    logger.info(f"Database: {settings.DATABASE_NAME}")


async def shutdown_event(app: FastAPI) -> None:
    """Application shutdown event."""
    logger.info("Shutting down MCP Service...")
    
    # Close MongoDB connection
    await close_mongo_connection()
    logger.info("Disconnected from MongoDB")