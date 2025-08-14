"""Embedding data models."""

from typing import List, Dict, Any
from datetime import datetime

from pydantic import Field, ConfigDict
from bson import ObjectId

from .base import DocumentBase


class EmbeddingCreate(DocumentBase):
    """Embedding creation model."""
    
    origin_type: str = Field(..., description="来源类型: task, memory")
    origin_id: str = Field(..., description="来源ID")
    text: str = Field(..., description="文本内容")
    embedding: List[float] = Field(..., description="嵌入向量")
    embedding_model: str = Field(..., description="嵌入模型名称")
    offset: int = Field(0, description="文本偏移量")
    chunk_size: int = Field(512, description="分块大小")


class Embedding(DocumentBase):
    """Embedding model as stored in database."""
    
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    project_id: str = Field(..., description="项目ID")
    origin_type: str = Field(..., description="来源类型: task, memory")
    origin_id: str = Field(..., description="来源ID")
    text: str = Field(..., description="文本内容") 
    embedding: List[float] = Field(..., description="嵌入向量")
    embedding_model: str = Field(..., description="嵌入模型名称")
    offset: int = Field(..., description="文本偏移量")
    chunk_size: int = Field(..., description="分块大小")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))

    model_config = ConfigDict(validate_by_name=True)