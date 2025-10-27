#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
速率限制器
支持令牌桶算法和固定窗口算法
"""

import time
import threading
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class RateLimitAlgorithm(Enum):
    """速率限制算法"""
    TOKEN_BUCKET = "token_bucket"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitStats:
    """速率限制统计"""
    total_requests: int = 0
    allowed_requests: int = 0
    denied_requests: int = 0
    wait_time: float = 0.0


class RateLimiter:
    """速率限制器"""
    
    def __init__(
        self,
        algorithm: str = "token_bucket",
        max_requests: int = 10,
        time_window: float = 1.0
    ):
        """
        初始化速率限制器
        
        Args:
            algorithm: 算法类型 (token_bucket, fixed_window)
            max_requests: 最大请求数
            time_window: 时间窗口（秒）
        """
        self.algorithm = RateLimitAlgorithm(algorithm)
        self.max_requests = max_requests
        self.time_window = time_window
        
        # 令牌桶算法参数
        self.tokens = max_requests
        self.last_refill = time.time()
        
        # 固定窗口算法参数
        self.window_start = time.time()
        self.requests_in_window = 0
        
        # 统计信息
        self.stats = RateLimitStats()
        self.lock = threading.Lock()
    
    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        等待直到可以发送请求
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否成功获取许可
        """
        start_time = time.time()
        
        while True:
            if self._can_make_request():
                with self.lock:
                    self.stats.allowed_requests += 1
                    self.stats.total_requests += 1
                return True
            
            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                with self.lock:
                    self.stats.denied_requests += 1
                    self.stats.total_requests += 1
                return False
            
            # 短暂休眠
            time.sleep(0.01)
    
    def _can_make_request(self) -> bool:
        """检查是否可以发送请求"""
        if self.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return self._token_bucket_can_make_request()
        else:
            return self._fixed_window_can_make_request()
    
    def _token_bucket_can_make_request(self) -> bool:
        """令牌桶算法"""
        current_time = time.time()
        
        # 计算需要补充的令牌
        time_passed = current_time - self.last_refill
        tokens_to_add = time_passed * (self.max_requests / self.time_window)
        
        # 补充令牌（不超过最大值）
        self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
        self.last_refill = current_time
        
        # 检查是否有可用令牌
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        
        return False
    
    def _fixed_window_can_make_request(self) -> bool:
        """固定窗口算法"""
        current_time = time.time()
        
        # 检查是否进入新窗口
        if current_time - self.window_start > self.time_window:
            self.window_start = current_time
            self.requests_in_window = 0
        
        # 检查窗口内请求数
        if self.requests_in_window < self.max_requests:
            self.requests_in_window += 1
            return True
        
        return False
    
    def get_stats(self) -> RateLimitStats:
        """获取统计信息"""
        return self.stats
    
    def reset_stats(self):
        """重置统计信息"""
        with self.lock:
            self.stats = RateLimitStats()


# 全局实例
_rate_limiter = None


def get_rate_limiter(
    algorithm: str = "token_bucket",
    max_requests: int = 10,
    time_window: float = 1.0
) -> RateLimiter:
    """获取速率限制器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            algorithm=algorithm,
            max_requests=max_requests,
            time_window=time_window
        )
    return _rate_limiter