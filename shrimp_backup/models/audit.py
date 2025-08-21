"""Audit logging models."""

from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import Field
from bson import ObjectId

from .base import DocumentBase


class AuditLog(DocumentBase):
    """Audit log model as stored in database."""
    
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    project_id: str = Field(..., description="项目ID")
    user: str = Field(..., description="操作用户ID")
    action: str = Field(..., description="操作类型")
    target: str = Field(..., description="目标对象ID")
    target_type: str = Field(..., description="目标对象类型: task, memory, workspace")
    payload: Dict[str, Any] = Field(..., description="操作负载")
    ip_address: Optional[str] = Field(None, description="操作IP")
    user_agent: Optional[str] = Field(None, description="用户代理")
    request_id: Optional[str] = Field(None, description="请求ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    

class AuditLogCreate(DocumentBase):
    """Audit log creation model."""
    
    project_id: str = Field(..., description="项目ID")
    user: str = Field(..., description="操作用户ID")
    action: str = Field(..., description="操作类型")
    target: str = Field(..., description="目标对象ID")
    target_type: str = Field(..., description="目标对象类型")
    payload: Dict[str, Any] = Field(..., description="操作负载")
    ip_address: Optional[str] = Field(None, description="操作IP")
    user_agent: Optional[str] = Field(None, description="用户代理")
    request_id: Optional[str] = Field(None, description="请求ID")