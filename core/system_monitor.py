#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业系统监控模块
实时监控CPU、内存、网络、磁盘等系统资源
参考MoviePilot的专业监控功能设计
"""

import psutil
import time
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, history_size: int = 3600):  # 保留1小时数据
        self.history_size = history_size
        self.monitoring = False
        self.monitor_thread = None
        
        # 历史数据存储
        self.cpu_history = deque(maxlen=history_size)
        self.memory_history = deque(maxlen=history_size)
        self.disk_history = deque(maxlen=history_size)
        self.network_history = deque(maxlen=history_size)
        
        # 系统信息
        self.system_info = self._get_system_info()
        
        # 监控间隔（秒）
        self.update_interval = 1
        
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统基本信息"""
        try:
            return {
                "platform": psutil.sys.platform,
                "system": f"{psutil.sys.platform} {psutil.sys.version}",
                "architecture": psutil.sys.architecture(),
                "cpu_count": {
                    "physical": psutil.cpu_count(logical=False),
                    "logical": psutil.cpu_count(logical=True)
                },
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available
                },
                "disk": {
                    "total": psutil.disk_usage('/').total if hasattr(psutil, 'disk_usage') else 0,
                    "free": psutil.disk_usage('/').free if hasattr(psutil, 'disk_usage') else 0
                },
                "boot_time": psutil.boot_time()
            }
        except Exception as e:
            return {
                "platform": "unknown",
                "system": "unknown",
                "architecture": "unknown",
                "cpu_count": {"physical": 0, "logical": 0},
                "memory": {"total": 0, "available": 0},
                "disk": {"total": 0, "free": 0},
                "boot_time": 0
            }
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """获取CPU使用率"""
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            cpu_times = psutil.cpu_times_percent(interval=None)
            
            return {
                "total": cpu_percent,
                "user": getattr(cpu_times, 'user', 0),
                "system": getattr(cpu_times, 'system', 0),
                "idle": getattr(cpu_times, 'idle', 0),
                "iowait": getattr(cpu_times, 'iowait', 0),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "total": 0,
                "user": 0,
                "system": 0,
                "idle": 100,
                "iowait": 0,
                "timestamp": time.time()
            }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent,
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_percent": swap.percent,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "total": 0,
                "available": 0,
                "used": 0,
                "percent": 0,
                "swap_total": 0,
                "swap_used": 0,
                "swap_percent": 0,
                "timestamp": time.time()
            }
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        try:
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            return {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
                "read_bytes": getattr(disk_io, 'read_bytes', 0),
                "write_bytes": getattr(disk_io, 'write_bytes', 0),
                "read_count": getattr(disk_io, 'read_count', 0),
                "write_count": getattr(disk_io, 'write_count', 0),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "total": 0,
                "used": 0,
                "free": 0,
                "percent": 0,
                "read_bytes": 0,
                "write_bytes": 0,
                "read_count": 0,
                "write_count": 0,
                "timestamp": time.time()
            }
    
    def get_network_usage(self) -> Dict[str, Any]:
        """获取网络使用情况"""
        try:
            net_io = psutil.net_io_counters()
            
            return {
                "bytes_sent": getattr(net_io, 'bytes_sent', 0),
                "bytes_recv": getattr(net_io, 'bytes_recv', 0),
                "packets_sent": getattr(net_io, 'packets_sent', 0),
                "packets_recv": getattr(net_io, 'packets_recv', 0),
                "errin": getattr(net_io, 'errin', 0),
                "errout": getattr(net_io, 'errout', 0),
                "dropin": getattr(net_io, 'dropin', 0),
                "dropout": getattr(net_io, 'dropout', 0),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "errin": 0,
                "errout": 0,
                "dropin": 0,
                "dropout": 0,
                "timestamp": time.time()
            }
    
    def get_process_info(self) -> List[Dict[str, Any]]:
        """获取进程信息"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    process_info = proc.info
                    processes.append({
                        "pid": process_info['pid'],
                        "name": process_info['name'],
                        "cpu_percent": process_info['cpu_percent'],
                        "memory_percent": process_info['memory_percent'],
                        "status": process_info['status']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 按CPU使用率排序，取前10
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            return processes[:10]
        except Exception as e:
            return []
    
    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        return {
            "system_info": self.system_info,
            "cpu": self.get_cpu_usage(),
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "network": self.get_network_usage(),
            "processes": self.get_process_info(),
            "uptime": time.time() - self.system_info.get('boot_time', 0),
            "timestamp": time.time()
        }
    
    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                # 收集监控数据
                cpu_data = self.get_cpu_usage()
                memory_data = self.get_memory_usage()
                disk_data = self.get_disk_usage()
                network_data = self.get_network_usage()
                
                # 添加到历史记录
                self.cpu_history.append(cpu_data)
                self.memory_history.append(memory_data)
                self.disk_history.append(disk_data)
                self.network_history.append(network_data)
                
                time.sleep(self.update_interval)
            except Exception as e:
                print(f"监控循环错误: {e}")
                time.sleep(self.update_interval)
    
    def get_history_data(self, metric: str, time_range: str = "1h") -> List[Dict[str, Any]]:
        """获取历史数据"""
        if metric == "cpu":
            history = self.cpu_history
        elif metric == "memory":
            history = self.memory_history
        elif metric == "disk":
            history = self.disk_history
        elif metric == "network":
            history = self.network_history
        else:
            return []
        
        # 根据时间范围过滤数据
        if time_range == "1h":
            cutoff_time = time.time() - 3600
        elif time_range == "6h":
            cutoff_time = time.time() - 6 * 3600
        elif time_range == "24h":
            cutoff_time = time.time() - 24 * 3600
        else:
            cutoff_time = 0
        
        return [data for data in history if data.get('timestamp', 0) >= cutoff_time]
    
    def get_trend_analysis(self) -> Dict[str, Any]:
        """获取趋势分析"""
        # 获取最近1小时的数据
        recent_cpu = self.get_history_data("cpu", "1h")
        recent_memory = self.get_history_data("memory", "1h")
        
        if not recent_cpu or not recent_memory:
            return {
                "cpu_trend": "stable",
                "memory_trend": "stable",
                "alerts": []
            }
        
        # 分析CPU趋势
        cpu_values = [data["total"] for data in recent_cpu]
        cpu_trend = self._analyze_trend(cpu_values)
        
        # 分析内存趋势
        memory_values = [data["percent"] for data in recent_memory]
        memory_trend = self._analyze_trend(memory_values)
        
        # 生成警报
        alerts = []
        if cpu_trend == "increasing" and cpu_values[-1] > 80:
            alerts.append({"type": "cpu", "level": "warning", "message": "CPU使用率持续上升且超过80%"})
        
        if memory_trend == "increasing" and memory_values[-1] > 85:
            alerts.append({"type": "memory", "level": "warning", "message": "内存使用率持续上升且超过85%"})
        
        return {
            "cpu_trend": cpu_trend,
            "memory_trend": memory_trend,
            "alerts": alerts
        }
    
    def _analyze_trend(self, values: List[float]) -> str:
        """分析趋势"""
        if len(values) < 2:
            return "stable"
        
        # 计算斜率
        x = list(range(len(values)))
        y = values
        
        # 简单线性回归
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x_i * x_i for x_i in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"


# 全局系统监控实例
system_monitor = SystemMonitor()