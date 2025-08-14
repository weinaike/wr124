import threading
from collections import defaultdict
import re
import json

def thread_safe_singleton(cls):
    """线程安全的单实例装饰器"""
    instances = {}
    lock = threading.Lock()  # 锁，用于线程安全

    def get_instance(*args, **kwargs):
        nonlocal instances
        if cls not in instances:
            with lock:  # 确保实例化过程是线程安全的
                if cls not in instances:  # 双重检查，防止重复创建
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def calculate_degrees(graph: dict[str, list[str]]) -> dict[str, tuple[int, int]]:
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)

    for node in graph:
        in_degree[node] = len(graph[node])
        for neighbor in graph[node]:
            out_degree[neighbor] += 1

    all_keys = set(in_degree.keys()).union(out_degree.keys())
    degree = {}
    for key in all_keys:
        first = 0
        second = 0
        if key in in_degree:
            first = in_degree[key]
        if key in out_degree:
            second = out_degree[key]
        degree[key] = (first, second)
    return degree


def get_json_content(data:str) -> dict:
    code_block_pattern = re.compile(rf'```json(.*?)```', re.DOTALL)
    json_blocks = code_block_pattern.findall(data)
    json_content = json.loads(''.join(json_blocks))
    return json_content