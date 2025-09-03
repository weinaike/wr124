#!/bin/bash

# 检查参数
if [ $# -eq 0 ]; then
    echo "用法: $0 <project_id>"
    echo "示例: $0 my_project"
    exit 1
fi

project_id=${1}
CONTAINER_NAME=${project_id}
project_dir=/media/wnk/projects/${project_id}

# 检查项目目录是否存在
if [ ! -d "$project_dir" ]; then
    echo "错误: 项目目录 $project_dir 不存在"
    exit 1
fi

echo "正在检查容器: $CONTAINER_NAME"
echo "项目目录: $project_dir"

# 标记是否需要在任务结束后停止容器
SHOULD_STOP_CONTAINER=false

# 检查容器是否已经存在并正在运行
if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo "容器 $CONTAINER_NAME 已在运行中，直接使用"
elif docker ps -a -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo "容器 $CONTAINER_NAME 存在但未启动，启动容器"
    docker start ${CONTAINER_NAME}
    SHOULD_STOP_CONTAINER=true
    echo "容器 $CONTAINER_NAME 已启动"
    # 等待容器完全启动
    sleep 2
else
    echo "容器不存在，创建并启动容器"
    SHOULD_STOP_CONTAINER=true
    
    # 启动容器（后台运行，保持运行状态）
    docker run -d --name ${CONTAINER_NAME} \
        -v $project_dir:/root/project \
        -v /usr/local/cuda-12.1:/usr/local/cuda \
        -v /home/wnk/.ssh:/root/.ssh \
        -e MCP_CLIENT_DOCKER=True \
        -e TZ=Asia/Shanghai \
        -e CUDA_HOME=/usr/local/cuda \
        --hostname ${CONTAINER_NAME} \
        --workdir /root/project \
        --gpus all \
        cppbuild:latest tail -f /dev/null
    
    echo "容器 $CONTAINER_NAME 已创建并启动"
    
    # 等待容器完全启动
    sleep 5
fi

echo "=== 开始执行深度分析智能体 ==="
python script/run_cpp_build.py \
    -t "深入研究代码库，分析其所提供的说明文档、安装文档、设计指南以及他们所引用与该代码库相关的网址。要求输出一份适合本操作系统使用的代码库编译安装指南（不要具体编译，要求输出指南文档，包含所有编译安装所涉及的所有环节），将文档写到项目根目录下取名Agent.md。如果Agent.md已经存在，则说明该任务已经完成，跳过该任务。代码库地址/root/project." \
    -p ${project_id} \
    -a wr124/agents/preset_agents/deep_researcher.md

sleep 60

echo "=== 开始执行项目构建智能体 ==="
python script/run_cpp_build.py \
    -t "项目地址:/root/project/.帮我完成该项目的cpp代码编译构建。编译构建过程中可能遇到各类问题：比如编译器版本、标准库版本、第三方库版本等，这些问题解决思路：先收集信息制定方案，方案确定后再开展具体修复工作。补充提示：该代码库是一个成熟代码库，优先从依赖问题入手，版本依赖可以根据需要调整，如果有可能尽量不要修改源代码，另外项目根目录中的Agent.md文件提供了编译安装指南。如果遇到棘手问题难以解决，search_agent具备网络检索能力，能够帮你定位问题。" \
    -p ${project_id} \
    -a wr124/agents/preset_agents/cpp_build_engineer.md 

echo "=== 所有任务执行完成 ==="

if [ "$SHOULD_STOP_CONTAINER" = true ]; then
    echo "停止容器: $CONTAINER_NAME"
    docker stop $CONTAINER_NAME
    echo "容器 $CONTAINER_NAME 已停止"
else
    echo "容器 $CONTAINER_NAME 保持运行状态（原本就在运行）"
fi