#!/usr/bin/env python3
"""
查询所有项目和任务信息，统计每个任务的耗时
耗时 = 最后更新时间 - 创建时间
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import pandas as pd
from tabulate import tabulate


#   - admin
#   - config
#   - gpt4o_agent_db
#   - iter_agent_db
#   - iter_agent_db_glm4_6
#   - local
#   - mcp_hard_cpp_build_db
#   - mcp_test_db
#   - shrimp_tasks

# MongoDB 连接配置
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "mcp_test_db")


async def get_all_projects(db) -> List[str]:
    """
    获取所有项目ID
    通过查询tasks集合中的不同project_id来获取所有项目
    """
    # 获取所有不同的 project_id
    project_ids = await db.tasks.distinct("project_id")
    return project_ids


async def get_project_tasks(db, project_id: str) -> List[Dict[str, Any]]:
    """
    获取指定项目的所有任务
    """
    tasks = []
    cursor = db.tasks.find({"project_id": project_id, "deleted_at": None})
    async for task in cursor:
        tasks.append(task)
    return tasks


def calculate_duration(created_at: datetime, updated_at: datetime) -> Dict[str, Any]:
    """
    计算任务耗时
    返回耗时的各种格式
    """
    if not created_at or not updated_at:
        return {
            "duration_seconds": 0,
            "duration_minutes": 0,
            "duration_hours": 0,
            "duration_days": 0,
            "duration_str": "N/A"
        }
    
    duration = updated_at - created_at
    duration_seconds = duration.total_seconds()
    
    # 计算天、小时、分钟、秒
    days = duration.days
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60
    
    # 格式化显示
    duration_parts = []
    if days > 0:
        duration_parts.append(f"{days}天")
    if hours > 0:
        duration_parts.append(f"{hours}小时")
    if minutes > 0:
        duration_parts.append(f"{minutes}分钟")
    if seconds > 0 or not duration_parts:
        duration_parts.append(f"{seconds}秒")
    
    duration_str = "".join(duration_parts)
    
    return {
        "duration_seconds": duration_seconds,
        "duration_minutes": duration_seconds / 60,
        "duration_hours": duration_seconds / 3600,
        "duration_days": duration_seconds / 86400,
        "duration_str": duration_str
    }


async def collect_statistics(db):
    """
    收集所有项目和任务的统计信息
    """
    all_statistics = []
    
    # 获取所有项目
    project_ids = await get_all_projects(db)
    print(f"\n找到 {len(project_ids)} 个项目\n")
    
    for project_id in project_ids:
        # 获取项目的所有任务
        tasks = await get_project_tasks(db, project_id)
        print(f"项目 {project_id}: 找到 {len(tasks)} 个任务")
        
        for task in tasks:
            # 计算耗时
            duration_info = calculate_duration(
                task.get("created_at"),
                task.get("updated_at")
            )
            
            # 收集统计信息
            stat = {
                "项目ID": project_id,
                "任务ID": str(task.get("_id")),
                "任务名称": task.get("name", "未命名"),
                "状态": task.get("status", "unknown"),
                "创建时间": task.get("created_at").strftime("%Y-%m-%d %H:%M:%S") if task.get("created_at") else "N/A",
                "更新时间": task.get("updated_at").strftime("%Y-%m-%d %H:%M:%S") if task.get("updated_at") else "N/A",
                "耗时": duration_info["duration_str"],
                "耗时(秒)": round(duration_info["duration_seconds"], 2),
                "耗时(分钟)": round(duration_info["duration_minutes"], 2),
                "耗时(小时)": round(duration_info["duration_hours"], 2),
                "耗时(天)": round(duration_info["duration_days"], 2),
                "版本号": task.get("version_number", 1),
                "会话ID": task.get("session_id", "N/A"),
            }
            
            all_statistics.append(stat)
    
    return all_statistics


def print_statistics(statistics: List[Dict[str, Any]]):
    """
    打印统计信息
    """
    if not statistics:
        print("没有找到任何任务数据")
        return
    
    print("\n" + "="*100)
    print("任务统计报告")
    print("="*100 + "\n")
    
    # 转换为 DataFrame 便于分析
    df = pd.DataFrame(statistics)
    
    # 1. 总体统计
    print("\n【总体统计】")
    print(f"项目总数: {df['项目ID'].nunique()}")
    print(f"任务总数: {len(df)}")
    print(f"平均耗时: {df['耗时'].iloc[0] if len(df) > 0 else 'N/A'}")
    print(f"平均耗时(小时): {df['耗时(小时)'].mean():.2f}")
    print(f"总耗时(小时): {df['耗时(小时)'].sum():.2f}")
    
    # 2. 按状态统计
    print("\n【按状态统计】")
    status_stats = df.groupby('状态').agg({
        '任务ID': 'count',
        '耗时(小时)': ['mean', 'sum', 'min', 'max']
    }).round(2)
    print(status_stats)
    
    # 3. 按项目统计
    print("\n【按项目统计】")
    project_stats = df.groupby('项目ID').agg({
        '任务ID': 'count',
        '耗时(小时)': ['mean', 'sum', 'min', 'max']
    }).round(2)
    print(project_stats)
    
    # 4. 详细任务列表（显示关键列）
    print("\n【任务详细列表】")
    display_df = df[['项目ID', '任务名称', '状态', '创建时间', '更新时间', '耗时']].head(50)
    print(tabulate(display_df, headers='keys', tablefmt='grid', showindex=False))
    
    if len(df) > 50:
        print(f"\n... 还有 {len(df) - 50} 个任务未显示")
    
    # 5. 耗时最长的10个任务
    print("\n【耗时最长的10个任务】")
    top_10 = df.nlargest(10, '耗时(小时)')[['项目ID', '任务名称', '状态', '耗时', '耗时(小时)']]
    print(tabulate(top_10, headers='keys', tablefmt='grid', showindex=False))
    
    # 6. 耗时最短的10个任务
    print("\n【耗时最短的10个任务】")
    bottom_10 = df.nsmallest(10, '耗时(小时)')[['项目ID', '任务名称', '状态', '耗时', '耗时(小时)']]
    print(tabulate(bottom_10, headers='keys', tablefmt='grid', showindex=False))


def save_to_csv(statistics: List[Dict[str, Any]], filename: str = None):
    """
    保存统计结果到CSV文件
    """
    if not statistics:
        print("没有数据可以保存")
        return
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"task_statistics_{timestamp}.csv"
    
    df = pd.DataFrame(statistics)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n统计结果已保存到: {filename}")


async def main():
    """
    主函数
    """
    print(f"连接到 MongoDB: {MONGO_URI}")
    print(f"数据库: {DATABASE_NAME}")
    
    # 连接数据库
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DATABASE_NAME]
    
    try:
        # 测试连接
        await client.admin.command('ping')
        print("数据库连接成功!")
        
        # 收集统计信息
        statistics = await collect_statistics(db)
        
        # 打印统计结果
        print_statistics(statistics)
        
        # 保存到CSV
        save_to_csv(statistics)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭连接
        client.close()
        print("\n数据库连接已关闭")


if __name__ == "__main__":
    asyncio.run(main())
