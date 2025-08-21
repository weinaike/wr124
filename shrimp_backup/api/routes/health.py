"""Health check endpoint."""

from fastapi import APIRouter
from shrimp.db.database import db_manager

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint - verifies database connectivity."""
    try:
        if db_manager.database is None:
            await db_manager.connect_to_mongo()
        
        # Test database connectivity
        await db_manager.client.admin.command('ping')
        
        # Quick check on main collections
        await db_manager.database.tasks.find_one({})
        
        return {
            "status": "healthy",
            "service": "mcp-service",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "mcp-service",
            "database": "disconnected",
            "error": str(e)
        }