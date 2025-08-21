"""Memory data models."""

from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import Field, ConfigDict
from bson import ObjectId

from .base import BaseModel, DocumentBase


class MemoryCreate(BaseModel):
    """Memory creation model."""
    
    task_id: Optional[str] = Field(None, description="关联的任务ID")
    title: str = Field(..., description="记忆标题")
    raw_text: str = Field(..., description="原始文本内容")
    goal: Optional[str] = Field(None, description="目标")
    actions: List[str] = Field(default_factory=list, description="执行的操作")
    outcome: Optional[str] = Field(None, description="结果")
    beneficial_ops: List[str] = Field(default_factory=list, description="有益操作")
    improvements: List[str] = Field(default_factory=list, description="改进建议")
    suggestions: Optional[str] = Field(None, description="建议")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class MemoryUpdate(BaseModel):
    """Memory update model."""
    
    title: Optional[str] = Field(None, description="记忆标题")
    raw_text: Optional[str] = Field(None, description="原始文本内容")
    goal: Optional[str] = Field(None, description="目标")
    actions: Optional[List[str]] = Field(None, description="执行的操作")
    outcome: Optional[str] = Field(None, description="结果")
    beneficial_ops: Optional[List[str]] = Field(None, description="有益操作")
    improvements: Optional[List[str]] = Field(None, description="改进建议")
    suggestions: Optional[str] = Field(None, description="建议")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class Memory(DocumentBase):
    """Memory model as stored in database."""
    
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    project_id: str = Field(..., description="项目ID")
    task_id: Optional[str] = Field(None, description="关联的任务ID")
    title: str = Field(..., description="记忆标题")
    raw_text: str = Field(..., description="原始文本内容")
    goal: Optional[str] = Field(None, description="目标")
    actions: List[str] = Field(default_factory=list, description="执行的操作")
    outcome: Optional[str] = Field(None, description="结果")
    beneficial_ops: List[str] = Field(default_factory=list, description="有益操作")
    improvements: List[str] = Field(default_factory=list, description="改进建议")
    suggestions: Optional[str] = Field(None, description="建议")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    embedding_model: Optional[str] = Field(None, description="嵌入模型")
    embedding: Optional[List[float]] = Field(None, description="嵌入向量")
    chunks: List[Dict[str, Any]] = Field(default_factory=list, description="文本分块")
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))

    model_config = ConfigDict(validate_by_name=True)