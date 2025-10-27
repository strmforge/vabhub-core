#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存管理系统
支持Redis和内存缓存
"""

import asyncio
import json
import pickle
from typing import Any, Optional, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from core.config import settings
import structlog

logger = structlog.get_logger()


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: dict = {}
        self.is_redis_available = False
        self.initialized = False
    
    async def initialize(self):
        """初始化缓存系统"""
        if self.initialized:
            return
        
        try:
            # 尝试连接Redis
            if settings.redis_url:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # 测试连接
                await self.redis_client.ping()
                self.is_redis_available = True
                logger.info("Redis缓存已启用", url=settings.redis_url)
            else:
                logger.info("Redis未配置，使用内存缓存")
        
        except Exception as e:
            logger.warning("Redis连接失败，使用内存缓存", error=str(e))
            self.is_redis_available = False
        
        self.initialized = True
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        if not self.initialized:
            await self.initialize()
        
        try:
            if self.is_redis_available and self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
            else:
                if key in self.memory_cache:
                    cache_data = self.memory_cache[key]
                    if cache_data['expires'] > datetime.now():
                        return cache_data['value']
                    else:
                        del self.memory_cache[key]
        
        except Exception as e:
            logger.error("获取缓存失败", key=key, error=str(e))
        
        return default
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.initialized:
            await self.initialize()
        
        if expire is None:
            expire = settings.cache_ttl
        
        try:
            if self.is_redis_available and self.redis_client:
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                
                await self.redis_client.setex(key, expire, value_str)
            else:
                expires_at = datetime.now() + timedelta(seconds=expire)
                self.memory_cache[key] = {
                    'value': value,
                    'expires': expires_at
                }
            
            return True
        
        except Exception as e:
            logger.error("设置缓存失败", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not self.initialized:
            await self.initialize()
        
        try:
            if self.is_redis_available and self.redis_client:
                await self.redis_client.delete(key)
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
            
            return True
        
        except Exception as e:
            logger.error("删除缓存失败", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.initialized:
            await self.initialize()
        
        try:
            if self.is_redis_available and self.redis_client:
                return await self.redis_client.exists(key) > 0
            else:
                if key in self.memory_cache:
                    cache_data = self.memory_cache[key]
                    if cache_data['expires'] > datetime.now():
                        return True
                    else:
                        del self.memory_cache[key]
        
        except Exception as e:
            logger.error("检查缓存存在失败", key=key, error=str(e))
        
        return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """递增缓存值"""
        if not self.initialized:
            await self.initialize()
        
        try:
            if self.is_redis_available and self.redis_client:
                return await self.redis_client.incrby(key, amount)
            else:
                current = await self.get(key, 0)
                new_value = current + amount
                await self.set(key, new_value)
                return new_value
        
        except Exception as e:
            logger.error("递增缓存失败", key=key, error=str(e))
            return None
    
    async def get_stats(self) -> dict:
        """获取缓存统计信息"""
        if not self.initialized:
            await self.initialize()
        
        stats = {
            'redis_available': self.is_redis_available,
            'memory_cache_size': len(self.memory_cache),
            'initialized': self.initialized
        }
        
        if self.is_redis_available and self.redis_client:
            try:
                info = await self.redis_client.info()
                stats.update({
                    'redis_version': info.get('redis_version'),
                    'used_memory': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients'),
                    'keyspace_hits': info.get('keyspace_hits'),
                    'keyspace_misses': info.get('keyspace_misses')
                })
            except Exception as e:
                logger.error("获取Redis统计信息失败", error=str(e))
        
        return stats


# 全局缓存管理器实例
cache_manager = CacheManager()