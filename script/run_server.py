#!/usr/bin/env python3
"""
MCP Service 启动脚本

启动多租户MCP服务器，支持任务管理、记忆管理和版本控制功能。

使用方式:
    python run_server.py                    # 使用默认配置启动
    python run_server.py --host 0.0.0.0    # 指定主机
    python run_server.py --port 8080       # 指定端口
    python run_server.py --dev             # 开发模式
"""

import argparse
import os
import sys
import asyncio
from pathlib import Path
import uvicorn
# 获取运行 目录
current_dir = os.getcwd()
# 添加项目根目录到Python路径
sys.path.insert(0, str(current_dir))



def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="启动MCP服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务器主机地址 (默认: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=4444,
        help="服务器端口 (默认: 4444)"
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        help="开发模式：启用调试日志和热重载"
    )
    
    parser.add_argument(
        "--protocol",
        choices=["http", "stdio"],
        default="http",
        help="通信协议 (默认: http)"
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    print("🚀 启动 MCP 服务器...")
    print(f"📡 协议: {args.protocol}")
    print(f"🏠 主机: {args.host}")
    print(f"🔌 端口: {args.port}")
    
    if args.dev:
        print("🔧 开发模式: 启用")
        # 可以在这里添加开发模式的特殊配置
    
    try:
        uvicorn.run(
            "shrimp.main:app",
            host=args.host,
            port=args.port,
            reload=args.dev,
        )
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()