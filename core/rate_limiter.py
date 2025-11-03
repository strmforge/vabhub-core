"""
VabHub API 限流模块
"""

import time
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from .logging_config import get_logger

logger = get_logger("vabhub.rate_limiter")


class RateLimiter:
    """API限流器"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        初始化限流器
        
        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
        
        logger.info(f"Rate limiter initialized: {max_requests} requests per {window_seconds} seconds")
    
    def is_rate_limited(self, client_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        检查客户端是否被限流
        
        Args:
            client_id: 客户端标识（IP地址或用户ID）
            
        Returns:
            (是否限流, 限流信息)
        """
        current_time = time.time()
        
        # 清理过期请求
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if current_time - req_time < self.window_seconds
            ]
        else:
            self.requests[client_id] = []
        
        # 检查是否超过限制
        if len(self.requests[client_id]) >= self.max_requests:
            # 计算剩余时间
            oldest_request = min(self.requests[client_id])
            reset_time = oldest_request + self.window_seconds
            remaining_time = int(reset_time - current_time)
            
            rate_limit_info = {
                "limit": self.max_requests,
                "remaining": 0,
                "reset_time": reset_time,
                "retry_after": remaining_time
            }
            
            logger.warning(
                f"Rate limit exceeded for client {client_id}",
                extra={
                    "client_id": client_id,
                    "requests_count": len(self.requests[client_id]),
                    "limit": self.max_requests,
                    "retry_after": remaining_time
                }
            )
            
            return True, rate_limit_info
        
        # 添加新请求
        self.requests[client_id].append(current_time)
        
        # 计算剩余请求数
        remaining = self.max_requests - len(self.requests[client_id])
        reset_time = current_time + self.window_seconds
        
        rate_limit_info = {
            "limit": self.max_requests,
            "remaining": remaining,
            "reset_time": reset_time,
            "retry_after": None
        }
        
        return False, rate_limit_info


def get_client_id(request: Request) -> str:
    """
    获取客户端标识
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        客户端标识（优先使用用户ID，否则使用IP地址）
    """
    # 优先使用认证用户ID
    if hasattr(request.state, 'user') and request.state.user:
        return f"user:{request.state.user.id}"
    
    # 使用IP地址作为备用标识
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


class RateLimitMiddleware:
    """限流中间件"""
    
    def __init__(self, app, rate_limiter: RateLimiter):
        self.app = app
        self.rate_limiter = rate_limiter
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope)
            
            # 跳过某些路径的限流检查
            if self._should_skip_rate_limit(request.url.path):
                return await self.app(scope, receive, send)
            
            client_id = get_client_id(request)
            is_limited, rate_info = self.rate_limiter.is_rate_limited(client_id)
            
            if is_limited:
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": "Too many requests",
                        "retry_after": rate_info["retry_after"]
                    }
                )
                
                # 添加限流头信息
                response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(int(rate_info["reset_time"]))
                response.headers["Retry-After"] = str(rate_info["retry_after"])
                
                await response(scope, receive, send)
                return
            
            # 添加限流信息到请求状态
            scope["rate_limit_info"] = rate_info
        
        await self.app(scope, receive, send)
    
    def _should_skip_rate_limit(self, path: str) -> bool:
        """检查是否应该跳过限流检查"""
        # 跳过健康检查、文档等路径
        skip_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        
        return any(path.startswith(skip_path) for skip_path in skip_paths)


# 全局限流器实例
default_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


def create_rate_limit_middleware(app, rate_limiter: Optional[RateLimiter] = None):
    """创建限流中间件"""
    if rate_limiter is None:
        rate_limiter = default_rate_limiter
    
    return RateLimitMiddleware(app, rate_limiter)


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    路由级别的限流装饰器
    
    Args:
        max_requests: 最大请求数
        window_seconds: 时间窗口（秒）
    """
    def decorator(func):
        # 为每个路由创建独立的限流器
        route_limiter = RateLimiter(max_requests, window_seconds)
        
        async def wrapper(*args, **kwargs):
            # 从参数中提取请求对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request is None:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                client_id = get_client_id(request)
                is_limited, rate_info = route_limiter.is_rate_limited(client_id)
                
                if is_limited:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Rate limit exceeded",
                            "message": "Too many requests for this endpoint",
                            "retry_after": rate_info["retry_after"]
                        }
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator