"""Task data models."""

from typing import Annotated, List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId

from .base import DocumentBase, PyObjectId


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TodoItem(BaseModel):
    """Todo item model. 代办项ID不建立数据库索引, id 仅用于任务代办内部区分。 """
    id: str = Field(..., description="代办事项ID")
    content: str = Field(..., description="待办事项内容")
    priority: Literal["low", "medium", "high"] = Field(..., description="待办事项优先级")
    status: Literal["pending", "in_progress", "completed"] = Field(..., description="待办事项状态")



class TaskCreate(BaseModel):
    """Task creation model."""
    
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    dependencies: List[str] = Field(default_factory=list, description="依赖任务列表")
    implementation_guide: Optional[str] = Field(None, description="实现指南")
    verification_criteria: Optional[str] = Field(None, description="验证标准")
    related_files: List[Dict[str, Any]] = Field(default_factory=list, description="相关文件列表")
    

class TaskUpdate(BaseModel):
    """Task update model."""
    
    name: Optional[str] = Field(None, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    status: Optional[Literal["pending", "in_progress", "completed"]] = Field(None, description="任务状态")
    dependencies: Optional[List[str]] = Field(None, description="依赖任务列表")
    notes: Optional[str] = Field(None, description="备注信息")
    implementation_guide: Optional[str] = Field(None, description="实现指南")
    verification_criteria: Optional[str] = Field(None, description="验证标准")
    related_files: Optional[List[Dict[str, Any]]] = Field(None, description="相关文件列表")
    summary: Optional[str] = Field(None, description="任务摘要")


class Task(DocumentBase):
    """Task model as stored in database."""
    
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    project_id: str = Field(..., description="项目ID")
    current_version_id: str = Field(..., description="当前版本ID")
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    dependencies: List[str] = Field(default_factory=list, description="依赖任务列表")
    notes: Optional[str] = Field(None, description="备注信息")
    implementation_guide: Optional[str] = Field(None, description="实现指南")
    verification_criteria: Optional[str] = Field(None, description="验证标准")
    related_files: List[Dict[str, Any]] = Field(default_factory=list, description="相关文件列表")
    summary: Optional[str] = Field(None, description="任务摘要")
    version_number: int = Field(default=1, description="版本号")
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    deleted_at: Optional[datetime] = Field(None, description="删除时间")
    todos: List[TodoItem] = Field(default_factory=list, description="待办事项列表")
    model_config = ConfigDict(populate_by_name=True)


