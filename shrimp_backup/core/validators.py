"""Task validation utilities."""

import re
from typing import List, Dict, Any, Optional
from enum import Enum

from shrimp.core.response import ValidationResult


class RelatedFileType(str, Enum):
    """Related file type enumeration."""
    TO_MODIFY = "TO_MODIFY"
    REFERENCE = "REFERENCE"  
    CREATE = "CREATE"
    DEPENDENCY = "DEPENDENCY"
    OTHER = "OTHER"


class TaskValidator:
    """任务验证器类"""
    
    @classmethod
    def validate_object_id(cls, task_id: str) -> bool:
        """验证MongoDB ObjectId格式（24字符hex字符串）"""
        if not task_id or not isinstance(task_id, str):
            return False
            
        task_id = task_id.strip()
        
        # Check for MongoDB ObjectId format (24 character hex string)
        if len(task_id) == 24:
            try:
                int(task_id, 16)  # Try to parse as hex
                return True
            except ValueError:
                return False
        
        return False
    
    @classmethod
    def validate_uuid(cls, task_id: str) -> bool:
        """向后兼容方法，实际调用validate_object_id"""
        return cls.validate_object_id(task_id)
    
    @classmethod
    def validate_dependencies(cls, dependencies: List[str]) -> ValidationResult:
        """验证任务依赖关系（统一使用ObjectId格式）"""
        result = ValidationResult(is_valid=True)
        
        if not dependencies:
            return result
            
        if not isinstance(dependencies, list):
            result.add_error("依赖关系必须是字符串列表")
            return result
        
        for dep_id in dependencies:
            if not isinstance(dep_id, str):
                result.add_error(f"依赖ID必须是字符串: {dep_id}")
            elif not cls.validate_object_id(dep_id.strip()):
                result.add_error(f"依赖ID格式无效（必须是24位hex ObjectId）: {dep_id}")
        
        # 检查重复依赖
        unique_deps = set(dep.strip() for dep in dependencies)
        if len(unique_deps) != len(dependencies):
            result.add_warning("存在重复的依赖关系")
            
        return result
    
    @classmethod  
    def validate_related_files(cls, related_files: List[Dict[str, Any]]) -> ValidationResult:
        """验证相关文件结构"""
        result = ValidationResult(is_valid=True)
        
        if not related_files:
            return result
            
        if not isinstance(related_files, list):
            result.add_error("相关文件必须是列表格式")
            return result
        
        for i, file_data in enumerate(related_files):
            if not isinstance(file_data, dict):
                result.add_error(f"文件 #{i+1}: 必须是字典格式")
                continue
                
            # 验证路径
            path = file_data.get('path', '').strip()
            if not path:
                result.add_error(f"文件 #{i+1}: 路径不能为空")
            
            # 验证文件类型
            file_type = file_data.get('type', '')
            try:
                RelatedFileType(file_type)
            except ValueError:
                valid_types = [t.value for t in RelatedFileType]
                result.add_error(f"文件 #{i+1}: 无效的文件类型 '{file_type}', 有效类型: {valid_types}")
            
            # 验证行号一致性
            line_start = file_data.get('line_start')
            line_end = file_data.get('line_end')
            
            if (line_start is not None) != (line_end is not None):
                result.add_error(f"文件 #{i+1}: line_start 和 line_end 必须同时提供或同时为空")
            
            if line_start is not None and line_end is not None:
                if not isinstance(line_start, int) or not isinstance(line_end, int):
                    result.add_error(f"文件 #{i+1}: 行号必须是整数")
                elif line_start > line_end:
                    result.add_error(f"文件 #{i+1}: 起始行号不能大于结束行号")
                elif line_start < 1:
                    result.add_error(f"文件 #{i+1}: 行号必须大于0")
                    
        return result
    
    @classmethod
    def validate_task_input(cls, task_data: Dict[str, Any], bulk: bool = False) -> ValidationResult:
        """验证任务输入数据"""
        result = ValidationResult(is_valid=True)
        
        # 验证名称
        name = task_data.get('name', '').strip() if task_data.get('name') else ''
        if not name:
            result.add_error("任务名称不能为空")
        elif len(name) > 100:
            result.add_error("任务名称过长，请限制在100个字符以内")
        
        # 验证描述
        description = task_data.get('description', '').strip() if task_data.get('description') else ''
        if description and len(description) < 10:
            result.add_warning("任务描述较短，建议提供更详细的内容")
        elif len(description) > 5000:
            result.add_error("任务描述过长，请限制在5000个字符以内")
        
        # 验证依赖关系
        if bulk is False:
            dependencies = task_data.get('dependencies', [])
            if dependencies:
                dep_result = cls.validate_dependencies(dependencies)
                if not dep_result.is_valid:
                    result.errors.extend(dep_result.errors)
                    result.is_valid = False
                result.warnings.extend(dep_result.warnings)
        
        # 验证相关文件  
        related_files = task_data.get('related_files', [])
        if related_files:
            files_result = cls.validate_related_files(related_files)
            if not files_result.is_valid:
                result.errors.extend(files_result.errors)
                result.is_valid = False
            result.warnings.extend(files_result.warnings)
        
        # 验证实现指南
        implementation_guide = task_data.get('implementation_guide', '').strip() if task_data.get('implementation_guide') else ''
        if implementation_guide and len(implementation_guide) > 10000:
            result.add_error("实现指南过长，请限制在10000个字符以内")
        
        # 验证验证标准
        verification_criteria = task_data.get('verification_criteria', '').strip() if task_data.get('verification_criteria') else ''
        if verification_criteria and len(verification_criteria) > 2000:
            result.add_error("验证标准过长，请限制在2000个字符以内")
        
        return result
    
    @classmethod
    def validate_task_score(cls, score: int) -> ValidationResult:
        """验证任务评分"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(score, int):
            result.add_error("评分必须是整数")
        elif not (0 <= score <= 100):
            result.add_error("评分必须在0到100之间")
            
        return result
    
    @classmethod
    def validate_task_summary(cls, summary: str) -> ValidationResult:
        """验证任务摘要"""
        result = ValidationResult(is_valid=True)
        
        if not summary or not isinstance(summary, str):
            result.add_error("任务摘要不能为空")
            return result
            
        summary = summary.strip()
        if len(summary) < 30:
            result.add_error("任务摘要必须至少包含30个字符")
        elif len(summary) > 1000:
            result.add_error("任务摘要过长，请限制在1000个字符以内")
            
        return result
