#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能队列管理器
实现优先级队列、任务调度和负载控制
"""

import time
import threading
import heapq
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import IntEnum


class Priority(IntEnum):
    """任务优先级"""
    CRITICAL = 10    # 关键任务
    HIGH = 7         # 高优先级
    NORMAL = 5       # 普通优先级
    LOW = 3          # 低优先级
    BACKGROUND = 1   # 后台任务


class TaskStatus(IntEnum):
    """任务状态"""
    PENDING = 0      # 等待中
    PROCESSING = 1   # 处理中
    COMPLETED = 2    # 已完成
    FAILED = 3       # 失败
    TIMEOUT = 4      # 超时
    CANCELLED = 5    # 已取消


@dataclass(order=True)
class Task:
    """任务对象"""
    priority: int = field(compare=True)
    created_at: float = field(compare=True)
    task_id: str = field(compare=False)
    user_id: str = field(default='', compare=False)
    data: Dict[str, Any] = field(default_factory=dict, compare=False)
    callback: Optional[Callable] = field(default=None, compare=False)
    timeout: int = field(default=30, compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    
    # 运行时状态
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    started_at: Optional[float] = field(default=None, compare=False)
    completed_at: Optional[float] = field(default=None, compare=False)
    result: Optional[Any] = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    
    def __post_init__(self):
        # 确保优先级为负数（用于最小堆实现最大优先级）
        self.priority = -abs(self.priority)
    
    def is_timeout(self) -> bool:
        """检查是否超时"""
        if self.started_at and self.timeout > 0:
            elapsed = time.time() - self.started_at
            return elapsed > self.timeout
        return False
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries
    
    def get_elapsed_time(self) -> float:
        """获取已用时间"""
        if self.started_at:
            end_time = self.completed_at or time.time()
            return end_time - self.started_at
        return 0.0


class PriorityQueue:
    """优先级队列（线程安全）"""
    
    def __init__(self):
        self._queue: List[Task] = []
        self._lock = threading.Lock()
        self._counter = 0  # 用于处理相同优先级的任务
    
    def put(self, task: Task):
        """添加任务到队列"""
        with self._lock:
            # 使用 counter 确保相同优先级按添加顺序处理
            heapq.heappush(self._queue, (task.priority, task.created_at, self._counter, task))
            self._counter += 1
    
    def get(self) -> Optional[Task]:
        """获取最高优先级任务"""
        with self._lock:
            if self._queue:
                _, _, _, task = heapq.heappop(self._queue)
                return task
            return None
    
    def peek(self) -> Optional[Task]:
        """查看最高优先级任务（不移除）"""
        with self._lock:
            if self._queue:
                return self._queue[0][3]
            return None
    
    def size(self) -> int:
        """获取队列大小"""
        with self._lock:
            return len(self._queue)
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        return self.size() == 0
    
    def clear(self):
        """清空队列"""
        with self._lock:
            self._queue.clear()
            self._counter = 0


class QueueManager:
    """队列管理器"""
    
    def __init__(self, max_workers: int = 4):
        """
        初始化队列管理器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self.queue = PriorityQueue()
        self.tasks: Dict[str, Task] = {}  # task_id -> Task
        self.workers: List[threading.Thread] = []
        self.running = False
        self.lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'timeout_tasks': 0,
            'cancelled_tasks': 0,
            'total_processing_time': 0.0,
        }
    
    def start(self):
        """启动队列管理器"""
        if self.running:
            print("⚠ 队列管理器已经在运行")
            return
        
        self.running = True
        
        # 启动工作线程
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"QueueWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        print(f"✓ 队列管理器已启动 ({self.max_workers} 个工作线程)")
    
    def stop(self, wait: bool = True):
        """停止队列管理器"""
        if not self.running:
            return
        
        self.running = False
        
        if wait:
            # 等待所有工作线程结束
            for worker in self.workers:
                worker.join(timeout=5)
        
        self.workers.clear()
        print("✓ 队列管理器已停止")
    
    def submit(
        self,
        task_id: str,
        data: Dict[str, Any],
        callback: Callable,
        priority: int = Priority.NORMAL,
        user_id: str = '',
        timeout: int = 30,
        max_retries: int = 3
    ) -> Task:
        """
        提交任务
        
        Args:
            task_id: 任务ID
            data: 任务数据
            callback: 回调函数
            priority: 优先级
            user_id: 用户ID
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            任务对象
        """
        task = Task(
            task_id=task_id,
            user_id=user_id,
            data=data,
            callback=callback,
            priority=priority,
            created_at=time.time(),
            timeout=timeout,
            max_retries=max_retries
        )
        
        with self.lock:
            self.tasks[task_id] = task
            self.stats['total_tasks'] += 1
        
        self.queue.put(task)
        
        print(f"✓ 任务已提交: {task_id} (优先级: {-task.priority})")
        return task
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.running:
            try:
                # 获取任务
                task = self.queue.get()
                
                if task is None:
                    time.sleep(0.1)  # 队列为空，短暂休眠
                    continue
                
                # 处理任务
                self._process_task(task)
                
            except Exception as e:
                print(f"⚠ 工作线程异常: {e}")
                time.sleep(1)
    
    def _process_task(self, task: Task):
        """处理任务"""
        try:
            # 更新状态
            task.status = TaskStatus.PROCESSING
            task.started_at = time.time()
            
            print(f"→ 开始处理任务: {task.task_id}")
            
            # 执行回调
            if task.callback:
                task.result = task.callback(task.data)
            
            # 检查超时
            if task.is_timeout():
                raise TimeoutError(f"任务超时 ({task.timeout}秒)")
            
            # 标记完成
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            
            with self.lock:
                self.stats['completed_tasks'] += 1
                self.stats['total_processing_time'] += task.get_elapsed_time()
            
            print(f"✓ 任务完成: {task.task_id} ({task.get_elapsed_time():.2f}秒)")
            
        except TimeoutError as e:
            task.status = TaskStatus.TIMEOUT
            task.error = str(e)
            
            with self.lock:
                self.stats['timeout_tasks'] += 1
            
            print(f"⏱ 任务超时: {task.task_id}")
            
        except Exception as e:
            task.error = str(e)
            
            # 检查是否可以重试
            if task.can_retry():
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.started_at = None
                
                print(f"↻ 任务重试 ({task.retry_count}/{task.max_retries}): {task.task_id}")
                
                # 重新加入队列（降低优先级）
                task.priority += 1  # 降低优先级
                self.queue.put(task)
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                
                with self.lock:
                    self.stats['failed_tasks'] += 1
                
                print(f"✗ 任务失败: {task.task_id} - {e}")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                self.stats['cancelled_tasks'] += 1
                print(f"✓ 任务已取消: {task_id}")
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            stats = self.stats.copy()
            stats['queue_size'] = self.queue.size()
            stats['active_workers'] = len([w for w in self.workers if w.is_alive()])
            
            if stats['completed_tasks'] > 0:
                stats['avg_processing_time'] = stats['total_processing_time'] / stats['completed_tasks']
            else:
                stats['avg_processing_time'] = 0.0
            
            return stats
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        print("\n📊 队列统计信息:")
        print(f"   总任务数: {stats['total_tasks']}")
        print(f"   已完成: {stats['completed_tasks']}")
        print(f"   失败: {stats['failed_tasks']}")
        print(f"   超时: {stats['timeout_tasks']}")
        print(f"   已取消: {stats['cancelled_tasks']}")
        print(f"   队列大小: {stats['queue_size']}")
        print(f"   活跃工作线程: {stats['active_workers']}")
        print(f"   平均处理时间: {stats['avg_processing_time']:.2f}秒")


# 全局队列管理器实例
_queue_manager = None


def get_queue_manager(max_workers: int = 4) -> QueueManager:
    """获取队列管理器实例（单例模式）"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager(max_workers=max_workers)
        _queue_manager.start()
    return _queue_manager


if __name__ == '__main__':
    # 测试队列管理器
    print("测试队列管理器")
    print("="*60)
    
    def sample_task(data):
        """示例任务"""
        print(f"  执行任务: {data.get('name', 'unknown')}")
        time.sleep(1)  # 模拟处理时间
        return f"任务完成: {data.get('name', 'unknown')}"
    
    # 创建队列管理器
    qm = get_queue_manager(max_workers=2)
    
    # 提交不同优先级的任务
    tasks = [
        ("task_high", {"name": "高优先级任务"}, Priority.HIGH),
        ("task_normal", {"name": "普通优先级任务"}, Priority.NORMAL),
        ("task_low", {"name": "低优先级任务"}, Priority.LOW),
        ("task_critical", {"name": "关键任务"}, Priority.CRITICAL),
    ]
    
    for task_id, data, priority in tasks:
        qm.submit(task_id, data, sample_task, priority=priority)
    
    # 等待任务完成
    time.sleep(5)
    
    # 打印统计信息
    qm.print_stats()
    
    # 停止队列管理器
    qm.stop()