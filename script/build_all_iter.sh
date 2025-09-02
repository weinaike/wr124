#!/bin/bash

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECTS_FILE="$SCRIPT_DIR/projects_iter.txt"
BUILD_SCRIPT="$SCRIPT_DIR/build_one_iter.sh"

# 检查必要文件是否存在
if [ ! -f "$PROJECTS_FILE" ]; then
    echo "错误: 项目列表文件不存在: $PROJECTS_FILE"
    exit 1
fi

if [ ! -f "$BUILD_SCRIPT" ]; then
    echo "错误: 构建脚本不存在: $BUILD_SCRIPT"
    exit 1
fi

# 检查构建脚本是否可执行
if [ ! -x "$BUILD_SCRIPT" ]; then
    echo "设置构建脚本为可执行..."
    chmod +x "$BUILD_SCRIPT"
fi

# 读取项目列表
echo "正在读取项目列表: $PROJECTS_FILE"
project_count=$(grep -v '^#' "$PROJECTS_FILE" | grep -v '^[[:space:]]*$' | wc -l)
echo "找到 $project_count 个项目"

# 统计变量
success_count=0
failed_count=0
skipped_count=0
failed_projects=()

echo "=== 开始批量构建项目 ==="

# 逐行读取项目并执行构建
while IFS= read -r line; do
    # 跳过空行和注释行
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    
    # 清理行首尾空格
    project_id=$(echo "$line" | xargs)
    
    echo ""
    echo "=================================================="
    echo "正在处理项目: $project_id"
    echo "=================================================="
    
    # 检查项目目录是否存在
    project_dir="/media/wnk/projects/${project_id}"
    if [ ! -d "$project_dir" ]; then
        echo "警告: 项目目录不存在，跳过项目: $project_dir"
        ((skipped_count++))
        continue
    fi
    
    # 执行构建脚本
    echo "执行: $BUILD_SCRIPT $project_id"
    if "$BUILD_SCRIPT" "$project_id"; then
        echo "✓ 项目 $project_id 构建成功"
        ((success_count++))
    else
        echo "✗ 项目 $project_id 构建失败"
        ((failed_count++))
        failed_projects+=("$project_id")
    fi
    
done < "$PROJECTS_FILE"

echo ""
echo "=================================================="
echo "批量构建完成统计"
echo "=================================================="
echo "总项目数: $project_count"
echo "成功: $success_count"
echo "失败: $failed_count"
echo "跳过: $skipped_count"

if [ ${#failed_projects[@]} -gt 0 ]; then
    echo ""
    echo "失败的项目:"
    for project in "${failed_projects[@]}"; do
        echo "  - $project"
    done
fi

echo ""
echo "批量构建任务完成!"

# 返回适当的退出码
if [ $failed_count -gt 0 ]; then
    exit 1
else
    exit 0
fi
