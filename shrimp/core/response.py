"""Unified service response formats."""

from typing import Generic, TypeVar, Optional, Any, Dict, List
from pydantic import BaseModel

T = TypeVar('T')


class ServiceResponse(BaseModel, Generic[T]):
    """统一的服务响应格式"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    code: int = 200
    message: Optional[str] = None
    
    @classmethod
    def success_response(cls, data: T, message: Optional[str] = None, code: int = 200) -> 'ServiceResponse[T]':
        """创建成功响应"""
        return cls(success=True, data=data, message=message, code=code)
    
    @classmethod
    def error_response(cls, error: str, code: int = 400, message: Optional[str] = None) -> 'ServiceResponse[T]':
        """创建错误响应"""
        return cls(success=False, error=error, code=code, message=message)
    
    @classmethod
    def validation_error(cls, error: str) -> 'ServiceResponse[T]':
        """创建验证错误响应"""
        return cls.error_response(error, code=422)
    
    @classmethod
    def not_found_error(cls, resource: str = "Resource") -> 'ServiceResponse[T]':
        """创建未找到错误响应"""
        return cls.error_response(f"{resource} not found", code=404)
    
    @classmethod
    def conflict_error(cls, error: str) -> 'ServiceResponse[T]':
        """创建冲突错误响应"""
        return cls.error_response(error, code=409)


class ValidationResult(BaseModel):
    """验证结果"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    
    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)
    
    @property
    def error_message(self) -> str:
        """获取错误信息字符串"""
        return "; ".join(self.errors) if self.errors else ""


class TaskOperationResult(BaseModel):
    """任务操作结果"""
    created: int = 0
    updated: int = 0
    deleted: int = 0
    failed: int = 0
    total: int = 0
    failures: List[Dict[str, Any]] = []
