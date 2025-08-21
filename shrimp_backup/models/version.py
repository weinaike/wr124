"""Task versioning models."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum

from pydantic import Field, ConfigDict
from bson import ObjectId

from .base import DocumentBase
from .task import Task


class OperationType(str, Enum):
    """Version operation type enumeration."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ROLLBACK = "rollback"


class TaskVersion(DocumentBase):
    """Task version model as stored in database."""
    
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    task_id: str = Field(..., description="原任务ID")
    project_id: str = Field(..., description="项目ID")
    payload: dict = Field(..., description="任务完整快照")
    operation: OperationType = Field(..., description="操作类型")
    changed_by: str = Field(..., description="操作者")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: Optional[str] = Field(None, description="提交信息")
    archived: bool = Field(default=False, description="是否已归档")

    model_config = ConfigDict(validate_by_name=True)


class TaskVersionCollection(DocumentBase):
    """Task version collection for pagination."""
    
    versions: List[TaskVersion]
    total: int
    page: int
    page_size: int
    has_next: bool