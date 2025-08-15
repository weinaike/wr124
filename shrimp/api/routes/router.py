"""API router assembly."""

from fastapi import APIRouter

from shrimp.api.routes.v1 import tasks, memories, versions
from shrimp.api.routes.health import router as health

router = APIRouter()

# Include all route modules with simplified paths
router.include_router(health, prefix="/api", tags=["health"])
router.include_router(tasks.router, prefix="/api", tags=["tasks"])
router.include_router(memories.router, prefix="/api", tags=["memories"])
router.include_router(versions.router, prefix="/api", tags=["versions"])