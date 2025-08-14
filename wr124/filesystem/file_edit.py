import os
from typing import Union, List, Dict, Any, Annotated, Optional
import logging
import difflib
try:
    from .utils import thread_safe_singleton
except ImportError:
    from utils import thread_safe_singleton

logger = logging.getLogger(__name__)

@thread_safe_singleton
class FileEditor:
    """
    文件编辑器类，按文件的绝对路径管理。每个文件会提供：最后一次编辑的原内容。以防止误操作，需要回退
    
    重要说明：
    - 所有方法的 file_path 参数必须是绝对路径
    - 不支持相对路径，相对路径会抛出 ValueError 异常
    - 这样可以确保路径处理的一致性和准确性
    """    
    def __init__(self):
        self.file_backup:Dict[str, str] = {}  # 存储文件的备份内容，key为文件路径，value为编辑前的原始内容

    def edit_file(self, file_path: str, patch_content: str) -> Dict[str, Any]:
        """
        编辑文件内容，应用补丁
        Args:
            file_path (str): 文件的绝对路径（必须是绝对路径，不支持相对路径）
            patch_content (str): 补丁内容，支持unified diff格式或直接文本替换
        Returns:
            Dict[str, Any]: 编辑结果，包含成功状态、消息、修改的行数等信息
        Raises:
            ValueError: 如果 file_path 不是绝对路径
        """
        try:
            # 验证路径必须是绝对路径
            if not os.path.isabs(file_path):
                raise ValueError(f"file_path must be an absolute path, got: {file_path}")
            
            # 规范化绝对路径
            file_path = os.path.abspath(file_path)
            
            # 读取原始文件内容，如果文件不存在则为空字符串
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            else:
                original_content = ''
                # 创建父目录
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 保存原始内容用于回退（只在第一次编辑时保存）
            # 如果文件已经在备份中，但备份内容与当前文件内容不一致，说明文件被外部修改了
            # 这种情况下我们需要更新备份为当前实际内容
            if file_path not in self.file_backup:
                self.file_backup[file_path] = original_content
            elif self.file_backup[file_path] != original_content:
                # 如果当前文件内容与备份不一致，并且当前文件确实存在且有内容，
                # 则更新备份为当前文件内容（外部修改的情况）
                if os.path.exists(file_path) and original_content:
                    self.file_backup[file_path] = original_content
            
            # 应用补丁
            if patch_content.startswith('---') or patch_content.startswith('+++'):
                # 处理unified diff格式的补丁
                result = self._apply_unified_diff(original_content, patch_content)
            else:
                # 处理直接文本替换或追加
                result = self._apply_text_patch(original_content, patch_content)
            
            if result['success']:
                # 写入修改后的内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result['new_content'])
                
                return {
                    'success': True,
                    'file_path': file_path,
                    'message': 'File edited successfully',
                    'lines_added': result.get('lines_added', 0),
                    'lines_removed': result.get('lines_removed', 0),
                    'lines_modified': result.get('lines_modified', 0),
                    'preview': self._get_edit_preview(original_content, result['new_content']),
                    'backup_available': True
                }
            else:
                return {
                    'success': False,
                    'file_path': file_path,
                    'error': result['error'],
                    'backup_available': file_path in self.file_backup
                }
            
        except Exception as e:
            logger.error(f"Edit file error: {e}")
            return {
                'success': False,
                'file_path': file_path,
                'error': f"Exception occurred while editing file: {str(e)}",
                'backup_available': file_path in self.file_backup
            }

    def rollback_file(self, file_path: str) -> Dict[str, Any]:
        """
        回退文件到上一次编辑前的原内容
        Args:
            file_path (str): 文件的绝对路径（必须是绝对路径，不支持相对路径）
        Returns:
            Dict[str, Any]: 回退结果
        Raises:
            ValueError: 如果 file_path 不是绝对路径
        """
        try:
            # 验证路径必须是绝对路径
            if not os.path.isabs(file_path):
                raise ValueError(f"file_path must be an absolute path, got: {file_path}")
            
            # 规范化绝对路径
            file_path = os.path.abspath(file_path)
            
            # 检查是否有备份
            if file_path not in self.file_backup:
                return {
                    'success': False,
                    'file_path': file_path,
                    'error': 'No backup available for this file. File has not been edited through FileEditor.'
                }
            
            # 恢复原始内容
            original_content = self.file_backup[file_path]
            
            # 写入原始内容
            if original_content == '':
                # 如果原始内容为空，说明文件原本不存在，删除文件
                if os.path.exists(file_path):
                    os.remove(file_path)
                message = 'File rolled back (deleted as it did not exist originally)'
            else:
                # 创建父目录（如果需要）
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                message = 'File rolled back to original content'
            
            # 清除备份（回退后不能再次回退）
            del self.file_backup[file_path]
            
            return {
                'success': True,
                'file_path': file_path,
                'message': message,
                'content_length': len(original_content)
            }
            
        except Exception as e:
            logger.error(f"Rollback file error: {e}")
            return {
                'success': False,
                'file_path': file_path,
                'error': f"Exception occurred while rolling back file: {str(e)}"
            }

    def _apply_unified_diff(self, original_content: str, patch_content: str) -> Dict[str, Any]:
        """
        应用unified diff格式的补丁
        Args:
            original_content (str): 原始文件内容
            patch_content (str): unified diff格式的补丁内容
        Returns:
            Dict[str, Any]: 应用结果
        """
        try:
            original_lines = original_content.splitlines(keepends=True)
            patch_lines = patch_content.splitlines()
            
            new_lines = []
            original_idx = 0
            lines_added = 0
            lines_removed = 0
            
            i = 0
            while i < len(patch_lines):
                line = patch_lines[i]
                
                if line.startswith('@@'):
                    # 解析hunk header: @@ -start,count +start,count @@
                    import re
                    match = re.match(r'@@\s*-(\d+)(?:,(\d+))?\s*\+(\d+)(?:,(\d+))?\s*@@', line)
                    if match:
                        old_start = int(match.group(1)) - 1  # 转换为0-based索引
                        # 跳到指定行之前，复制未修改的行
                        while original_idx < old_start and original_idx < len(original_lines):
                            new_lines.append(original_lines[original_idx])
                            original_idx += 1
                elif line.startswith('---') or line.startswith('+++'):
                    # 跳过文件头
                    pass
                elif line.startswith('-'):
                    # 删除行 - 跳过原文件中的这一行
                    if original_idx < len(original_lines):
                        original_idx += 1
                        lines_removed += 1
                elif line.startswith('+'):
                    # 添加行 - 将新行添加到结果中
                    new_content = line[1:]  # 移除 + 符号
                    if not new_content.endswith('\n'):
                        new_content += '\n'
                    new_lines.append(new_content)
                    lines_added += 1
                elif line.startswith(' '):
                    # 上下文行 - 保持不变
                    if original_idx < len(original_lines):
                        new_lines.append(original_lines[original_idx])
                        original_idx += 1
                elif line == '':
                    # 空行，跳过
                    pass
                
                i += 1
            
            # 添加剩余的原始内容
            while original_idx < len(original_lines):
                new_lines.append(original_lines[original_idx])
                original_idx += 1
            
            return {
                'success': True,
                'new_content': ''.join(new_lines),
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'lines_modified': 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to apply unified diff: {str(e)}"
            }

    def _apply_text_patch(self, original_content: str, patch_content: str) -> Dict[str, Any]:
        """
        应用简单的文本替换或追加
        Args:
            original_content (str): 原始文件内容
            patch_content (str): 要应用的文本内容
        Returns:
            Dict[str, Any]: 应用结果
        """
        try:
            # 如果原始内容为空，直接使用补丁内容
            if not original_content:
                return {
                    'success': True,
                    'new_content': patch_content,
                    'lines_added': len(patch_content.splitlines()),
                    'lines_removed': 0,
                    'lines_modified': 0
                }
            
            # 简单的追加模式
            new_content = original_content.rstrip() + '\n' + patch_content
            
            return {
                'success': True,
                'new_content': new_content,
                'lines_added': len(patch_content.splitlines()),
                'lines_removed': 0,
                'lines_modified': 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to apply text patch: {str(e)}"
            }

    def _get_edit_preview(self, original_content: str, new_content: str, context_lines: int = 3) -> str:
        """
        生成编辑预览，显示修改前后的差异
        Args:
            original_content (str): 原始内容
            new_content (str): 修改后的内容
            context_lines (int): 上下文行数
        Returns:
            str: 差异预览
        """
        try:
            original_lines = original_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            
            # 使用difflib生成unified diff
            diff = difflib.unified_diff(
                original_lines,
                new_lines,
                fromfile='original',
                tofile='modified',
                n=context_lines
            )
            
            diff_lines = list(diff)
            if len(diff_lines) > 50:  # 限制预览长度
                diff_lines = diff_lines[:50] + ['... (preview truncated)\n']
            
            return ''.join(diff_lines)
            
        except Exception as e:
            return f"Error generating preview: {str(e)}"

    def list_backups(self) -> Dict[str, int]:
        """
        列出所有可回退的文件及其备份内容长度
        Returns:
            Dict[str, int]: 文件路径到备份内容长度的映射
        """
        return {file_path: len(content) for file_path, content in self.file_backup.items()}
    
    def clear_backups(self) -> Dict[str, Any]:
        """
        清除所有备份
        Returns:
            Dict[str, Any]: 清除结果
        """
        backup_count = len(self.file_backup)
        self.file_backup.clear()
        return {
            'success': True,
            'message': f'Cleared {backup_count} backup(s)',
            'backup_count': backup_count
        }
    
    def clear_backup(self, file_path: str) -> Dict[str, Any]:
        """
        清除指定文件的备份
        Args:
            file_path (str): 文件路径（必须是绝对路径，不支持相对路径）
        Returns:
            Dict[str, Any]: 清除结果
        Raises:
            ValueError: 如果 file_path 不是绝对路径
        """
        # 验证路径必须是绝对路径
        if not os.path.isabs(file_path):
            raise ValueError(f"file_path must be an absolute path, got: {file_path}")
        
        # 规范化绝对路径
        file_path = os.path.abspath(file_path)
        
        if file_path in self.file_backup:
            del self.file_backup[file_path]
            return {
                'success': True,
                'file_path': file_path,
                'message': 'Backup cleared successfully'
            }
        else:
            return {
                'success': False,
                'file_path': file_path,
                'message': 'No backup found for this file'
            }
        
    


    

async def merge_patch(patch_str: Annotated[str, "The patch content as a string"],
                      target_file: Annotated[str, "The target file to apply the patch to"],
                      explanation: Annotated[str, "One sentence explanation as to why this tool is being used, and how it contributes to the goal."] = ""
                      ) -> Dict[str, Any]:
    """
    应用补丁到目标文件，支持两种补丁格式
    
    Args:
        patch_str (str): 补丁内容，支持以下两种格式：
            
            1. **文本追加格式** (推荐用于添加新内容)：
               - 直接文本内容，将被追加到文件末尾
               - 如果目标文件不存在，则创建新文件
               - 示例:
                 ```
                 def new_function():
                     return "Hello"
                 ```
            
            2. **Unified Diff 格式** (推荐用于精确修改)：
               - 标准的 Git-style diff 格式
               - 必须以 '---' 或 '+++' 开头
               - 支持多个 hunk (@@ 块)
               - 格式要求:
                 ```
                 --- original_file
                 +++ modified_file
                 @@ -start_line,line_count +start_line,line_count @@
                  context_line
                 -deleted_line
                 +added_line
                  context_line
                 ```
               - 示例:
                 ```
                 --- original
                 +++ modified
                 @@ -1,3 +1,4 @@
                  def hello():
                 +    print("Debug info")
                      return "world"
                 ```
        
        target_file (str): 目标文件路径
            - **必须是绝对路径，不支持相对路径**
            - 相对路径会导致错误返回
            - 如果文件不存在会自动创建（包括父目录）
            - 示例: "/home/user/project/file.txt"
        
        explanation (Optional[str]): 操作说明（可选）
            - 用于记录此次编辑操作的目的
            - 不影响实际操作，仅用于日志或调试
    
    Returns:
        Dict[str, Any]: 编辑结果字典，包含以下字段：
            - success (bool): 操作是否成功
            - file_path (str): 实际操作的文件绝对路径
            - message (str): 操作结果消息
            - lines_added (int): 添加的行数
            - lines_removed (int): 删除的行数  
            - lines_modified (int): 修改的行数
            - preview (str): 编辑预览（unified diff 格式）
            - backup_available (bool): 是否有备份可用于回退
            - error (str): 错误信息（仅在 success=False 时存在）
    
    补丁格式详细说明:
        
        **文本追加模式:**
        - 适用场景: 在文件末尾添加新内容
        - 处理逻辑: original_content + '\n' + patch_content
        - 自动处理换行符
        
        **Unified Diff 模式:**
        - 适用场景: 精确的行级别修改
        - 支持的操作:
          * 添加行: 以 '+' 开头
          * 删除行: 以 '-' 开头  
          * 上下文行: 以 ' ' 开头
          * Hunk 头: @@ -old_start,old_count +new_start,new_count @@
        - 注意事项:
          * 行号从 1 开始计数
          * 上下文行必须完全匹配
          * 支持多个 hunk 块
    
    备份机制:
        - 首次编辑时自动创建文件备份
        - 支持使用 rollback_merge_patch() 回退
        - 单例模式确保备份状态一致性
    
    异常处理:
        - 文件读写权限问题
        - 补丁格式错误
        - 路径不存在或无效
        - 所有异常都会返回详细的错误信息
    
    使用示例:
        ```python
        # 文本追加
        result = await merge_patch(
            "print('New line')",
            "script.py"
        )
        
        # Unified diff
        diff_patch = '''--- original
        +++ modified  
        @@ -1,2 +1,3 @@
         print("Hello")
        +print("World")
         print("End")
        '''
        result = await merge_patch(diff_patch, "script.py")
        ```
    """
    fileedit = FileEditor()
    
    # 验证路径必须是绝对路径
    if not os.path.isabs(target_file):
        return {
            'success': False,
            'file_path': target_file,
            'error': f"target_file must be an absolute path, got relative path: {target_file}. Please provide an absolute path.",
            'backup_available': False
        }
    
    return fileedit.edit_file(target_file, patch_str)
    

async def rollback_merge_patch(target_file: Annotated[str, "The target file to rollback the patch from"],
                            explanation: Annotated[str, "One sentence explanation as to why this tool is being used, and how it contributes to the goal."] = ""
                            ) -> Dict[str, Any]:
    """
    将文件回退到上一次编辑前的原始状态
    
    Args:
        target_file (str): 目标文件路径
            - **必须是绝对路径，不支持相对路径**
            - 相对路径会导致错误返回
            - 必须是之前通过 merge_patch() 编辑过的文件
            - 示例: "/home/user/project/file.txt"
            
        explanation (Optional[str]): 操作说明（可选）
            - 用于记录此次回退操作的目的
            - 不影响实际操作，仅用于日志或调试
    
    Returns:
        Dict[str, Any]: 回退结果字典，包含以下字段：
            - success (bool): 操作是否成功
            - file_path (str): 实际操作的文件绝对路径
            - message (str): 操作结果消息
            - content_length (int): 恢复内容的字符长度（成功时）
            - error (str): 错误信息（仅在 success=False 时存在）
    
    回退行为说明:
        
        **原文件存在的情况:**
        - 恢复到首次编辑前的原始内容
        - 保持原文件的编码格式 (UTF-8)
        - 自动创建必要的父目录
        
        **原文件不存在的情况:**  
        - 删除当前文件（因为原本不存在）
        - message 会包含 "deleted as it did not exist originally"
        
        **备份清除:**
        - 回退成功后会自动清除该文件的备份
        - 同一文件不能进行多次回退
        - 需要重新编辑后才能再次回退
    
    错误情况:
        - 文件未通过 FileEditor 编辑过（无备份）
        - 文件路径无效或权限不足
        - 备份数据损坏或不一致
    
    使用示例:
        ```python
        # 先编辑文件
        await merge_patch("new content", "test.txt")
        
        # 回退到编辑前状态
        result = await rollback_merge_patch("test.txt")
        if result['success']:
            print(f"回退成功: {result['message']}")
        ```
    
    注意事项:
        - 回退是不可逆操作
        - 确保在回退前保存当前重要修改
        - FileEditor 使用单例模式，备份在进程生命周期内有效
    """
    fileedit = FileEditor()
    
    # 验证路径必须是绝对路径
    if not os.path.isabs(target_file):
        return {
            'success': False,
            'file_path': target_file,
            'error': f"target_file must be an absolute path, got relative path: {target_file}. Please provide an absolute path.",
            'backup_available': False
        }
    
    return fileedit.rollback_file(target_file)


