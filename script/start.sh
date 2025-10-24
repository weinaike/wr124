    # 启动容器（后台运行，保持运行状态）
    docker run -d --name mongo \
        -v /media/wnk/projects/mongo:/root/project \
        -v /usr/local/cuda-12.1:/usr/local/cuda \
        -v /home/wnk/.ssh:/root/.ssh \
        -e MCP_CLIENT_DOCKER=True \
        -e TZ=Asia/Shanghai \
        -e CUDA_HOME=/usr/local/cuda \
        --hostname mongo \
        --workdir /root/project \
        --gpus all \
        cppbuild:latest tail -f /dev/null