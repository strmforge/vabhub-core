"""
GraphQL API for VabHub Core - Enhanced Edition
"""

import strawberry
import logging
import time
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from strawberry.fastapi import GraphQLRouter
from strawberry.extensions import Extension
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from .graphql_schema import schema
from .config import Config, get_config_by_env
from .cache_manager import CacheBackend, RedisCacheBackend, MemoryCacheBackend

# 配置缓存和日志
logger = logging.getLogger(__name__)


# 全局GraphQL订阅管理器
class SubscriptionManager:
    """管理GraphQL实时订阅的管理器 - 增强版（带缓存功能）"""

    def __init__(self):
        self.active_subscriptions: Dict[str, WebSocket] = {}
        self.broadcast_channels: Dict[str, List[str]] = {}
        self.lock = asyncio.Lock()
        self.subscription_metadata: Dict[str, Dict[str, Any]] = {}
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "channels": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "cached_messages": 0,
        }
        # 添加订阅缓存功能
        self.subscription_cache: Dict[str, Dict[str, Any]] = {
            "by_channel": {},  # 按频道缓存消息
            "ttl": 30000,  # 缓存TTL (毫秒)
        }

    async def register_subscription(
        self,
        subscription_id: str,
        websocket: WebSocket,
        metadata: Dict[str, Any] = None,
    ):
        """注册新的订阅连接"""
        async with self.lock:
            self.active_subscriptions[subscription_id] = websocket
            self.subscription_metadata[subscription_id] = metadata or {}
            self.stats["total_connections"] += 1
            self.stats["active_connections"] += 1
            logger.debug(
                f"Subscription registered: {subscription_id} with metadata: {metadata}"
            )

    async def unsubscribe_from_channel(self, subscription_id: str, channel: str):
        """取消订阅广播频道"""
        async with self.lock:
            if (
                channel in self.broadcast_channels
                and subscription_id in self.broadcast_channels[channel]
            ):
                self.broadcast_channels[channel].remove(subscription_id)
                logger.debug(
                    f"Subscription {subscription_id} unsubscribed from channel {channel}"
                )
                # 更新统计信息
                if (
                    channel in self.stats["channels"]
                    and self.stats["channels"][channel] > 0
                ):
                    self.stats["channels"][channel] -= 1

    async def subscribe_to_channel(self, subscription_id: str, channel: str):
        """订阅广播频道"""
        async with self.lock:
            if channel not in self.broadcast_channels:
                self.broadcast_channels[channel] = []
            if subscription_id not in self.broadcast_channels[channel]:
                self.broadcast_channels[channel].append(subscription_id)
                # 更新统计信息
                if channel not in self.stats["channels"]:
                    self.stats["channels"][channel] = 0
                self.stats["channels"][channel] += 1
                logger.debug(
                    f"Subscription {subscription_id} subscribed to channel {channel}"
                )

    async def unregister_subscription(self, subscription_id: str):
        """注销订阅连接"""
        async with self.lock:
            if subscription_id in self.active_subscriptions:
                del self.active_subscriptions[subscription_id]
            if subscription_id in self.subscription_metadata:
                del self.subscription_metadata[subscription_id]

            # 从所有频道中移除
            for channel, subscribers in self.broadcast_channels.items():
                if subscription_id in subscribers:
                    subscribers.remove(subscription_id)
                    if (
                        channel in self.stats["channels"]
                        and self.stats["channels"][channel] > 0
                    ):
                        self.stats["channels"][channel] -= 1

            self.stats["active_connections"] = max(
                0, self.stats["active_connections"] - 1
            )
            logger.debug(f"Subscription unregistered: {subscription_id}")

    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """向频道广播消息（带缓存功能）"""
        # 检查缓存
        cache_key = f"channel:{channel}:{message.get('type', 'default')}"
        current_time = time.time() * 1000

        # 检查是否需要缓存此消息
        if self._should_cache_message(channel, message):
            self.subscription_cache["by_channel"][cache_key] = {
                "message": message,
                "timestamp": current_time,
                "ttl": self.subscription_cache["ttl"],
            }
            self.stats["cached_messages"] += 1

        # 获取频道订阅者
        subscribers = self.broadcast_channels.get(channel, []).copy()

        if not subscribers:
            logger.debug(f"No subscribers for channel {channel}")
            return

        # 发送消息给所有订阅者
        disconnected_subscribers = []

        for subscription_id in subscribers:
            if subscription_id in self.active_subscriptions:
                websocket = self.active_subscriptions[subscription_id]
                try:
                    await websocket.send_text(json.dumps(message))
                    self.stats["messages_sent"] += 1
                    logger.debug(
                        f"Message sent to subscription {subscription_id} on channel {channel}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to send message to subscription {subscription_id}: {e}"
                    )
                    disconnected_subscribers.append(subscription_id)
            else:
                disconnected_subscribers.append(subscription_id)

        # 清理断开的连接
        for subscription_id in disconnected_subscribers:
            await self.unregister_subscription(subscription_id)

    def _should_cache_message(self, channel: str, message: Dict[str, Any]) -> bool:
        """判断是否应该缓存消息"""
        # 只缓存特定类型的消息
        cacheable_types = ["status_update", "progress_update", "system_notification"]
        return message.get("type") in cacheable_types

    async def get_cached_messages(
        self, channel: str, since_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """获取缓存的频道消息"""
        cached_messages = []
        current_time = time.time() * 1000

        for cache_key, cache_data in self.subscription_cache["by_channel"].items():
            if cache_key.startswith(f"channel:{channel}:"):
                # 检查缓存是否过期
                if current_time - cache_data["timestamp"] < cache_data["ttl"]:
                    # 检查时间戳过滤
                    if (
                        since_timestamp is None
                        or cache_data["timestamp"] > since_timestamp
                    ):
                        cached_messages.append(cache_data["message"])
                        self.stats["cache_hits"] += 1
                else:
                    # 清理过期缓存
                    del self.subscription_cache["by_channel"][cache_key]

        if not cached_messages:
            self.stats["cache_misses"] += 1

        return cached_messages

    async def get_subscription_stats(self) -> Dict[str, Any]:
        """获取订阅统计信息"""
        return {
            "stats": self.stats,
            "active_channels": list(self.broadcast_channels.keys()),
            "total_subscriptions": len(self.active_subscriptions),
            "subscription_metadata": self.subscription_metadata,
        }


# 全局订阅管理器实例
subscription_manager = SubscriptionManager()


# GraphQL扩展类
class LoggingExtension(Extension):
    """GraphQL查询日志扩展"""

    def on_request_start(self):
        self.start_time = time.time()

    def on_request_end(self):
        execution_time = time.time() - self.start_time
        logger.info(f"GraphQL query executed in {execution_time:.3f}s")


class CacheExtension(Extension):
    """GraphQL查询缓存扩展"""

    def __init__(self, cache_backend: CacheBackend):
        self.cache_backend = cache_backend

    async def resolve(self, _next, root, info, *args, **kwargs):
        # 生成缓存键
        cache_key = self._generate_cache_key(info, args, kwargs)

        # 尝试从缓存获取
        cached_result = await self.cache_backend.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {cache_key}")
            return cached_result

        # 执行查询并缓存结果
        result = await _next(root, info, *args, **kwargs)
        await self.cache_backend.set(cache_key, result, ttl=300)  # 5分钟缓存

        return result

    def _generate_cache_key(self, info, args, kwargs) -> str:
        """生成缓存键"""
        import hashlib

        key_data = {
            "operation_name": (
                info.operation.name.value
                if info.operation and info.operation.name
                else "anonymous"
            ),
            "field_name": info.field_name,
            "args": str(args),
            "kwargs": str(kwargs),
            "variables": str(info.variable_values),
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return f"graphql:{hashlib.md5(key_string.encode()).hexdigest()}"


# GraphQL WebSocket连接管理器
class GraphQLWebSocketManager:
    """管理GraphQL WebSocket连接"""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def connect(
        self, websocket: WebSocket, connection_params: Dict[str, Any] = None
    ):
        """建立WebSocket连接"""
        connection_id = str(uuid.uuid4())

        await websocket.accept()

        async with self.lock:
            self.connections[connection_id] = websocket
            self.connection_metadata[connection_id] = {
                "connected_at": datetime.now().isoformat(),
                "params": connection_params or {},
                "last_activity": time.time(),
            }

        logger.info(f"GraphQL WebSocket connection established: {connection_id}")
        return connection_id

    async def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        async with self.lock:
            if connection_id in self.connections:
                del self.connections[connection_id]
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]

        logger.info(f"GraphQL WebSocket connection closed: {connection_id}")

    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """向特定连接发送消息"""
        if connection_id in self.connections:
            websocket = self.connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
                # 更新活动时间
                self.connection_metadata[connection_id]["last_activity"] = time.time()
            except Exception as e:
                logger.error(
                    f"Failed to send message to connection {connection_id}: {e}"
                )
                await self.disconnect(connection_id)

    async def broadcast(self, message: Dict[str, Any]):
        """向所有连接广播消息"""
        connection_ids = list(self.connections.keys())

        for connection_id in connection_ids:
            await self.send_message(connection_id, message)

    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            "total_connections": len(self.connections),
            "connection_metadata": self.connection_metadata,
        }


# 创建GraphQL路由器
class VabHubGraphQLRouter(GraphQLRouter):
    """VabHub定制的GraphQL路由器"""

    def __init__(self, schema, **kwargs):
        super().__init__(schema, **kwargs)

        # 添加自定义中间件
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket端点处理"""
        await websocket.accept()

        try:
            # 处理GraphQL over WebSocket协议
            protocol = websocket.headers.get("sec-websocket-protocol", "")

            if GRAPHQL_TRANSPORT_WS_PROTOCOL in protocol:
                await self._handle_graphql_transport_ws(websocket)
            elif GRAPHQL_WS_PROTOCOL in protocol:
                await self._handle_graphql_ws(websocket)
            else:
                # 默认协议处理
                await self._handle_default_ws(websocket)

        except WebSocketDisconnect:
            logger.info("WebSocket connection closed by client")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=1011)

    async def _handle_graphql_transport_ws(self, websocket: WebSocket):
        """处理GraphQL传输WebSocket协议"""
        # 实现GraphQL传输协议逻辑
        pass

    async def _handle_graphql_ws(self, websocket: WebSocket):
        """处理GraphQL WebSocket协议"""
        # 实现GraphQL WebSocket协议逻辑
        pass

    async def _handle_default_ws(self, websocket: WebSocket):
        """处理默认WebSocket协议"""
        # 实现默认WebSocket处理逻辑
        pass


# 创建GraphQL应用
class VabHubGraphQLApp:
    """VabHub GraphQL应用"""

    def __init__(self, config: Config):
        self.config = config
        self.app = FastAPI(title="VabHub GraphQL API", version="1.0.0")

        # 创建GraphQL Schema
        self.schema = self._create_schema()

        # 创建GraphQL路由器
        self.router = VabHubGraphQLRouter(
            self.schema,
            graphiql=True,
            subscription_protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL],
        )

        # 设置路由
        self.app.include_router(self.router, prefix="/graphql")

        # 添加健康检查端点
        self._add_health_endpoints()

        # 添加监控端点
        self._add_monitoring_endpoints()

    def _create_schema(self):
        """创建GraphQL Schema"""
        # 这里应该导入并组合所有GraphQL类型
        # 暂时返回一个基础schema
        return schema

    def _add_health_endpoints(self):
        """添加健康检查端点"""

        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

        @self.app.get("/health/detailed")
        async def detailed_health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "graphql": {
                    "subscriptions": await subscription_manager.get_subscription_stats(),
                    "cache": {
                        "hits": subscription_manager.stats["cache_hits"],
                        "misses": subscription_manager.stats["cache_misses"],
                        "cached_messages": subscription_manager.stats[
                            "cached_messages"
                        ],
                    },
                },
            }

    def _add_monitoring_endpoints(self):
        """添加监控端点"""

        @self.app.get("/metrics")
        async def metrics():
            """GraphQL API指标"""
            return {
                "graphql": {
                    "subscriptions": await subscription_manager.get_subscription_stats(),
                    "uptime": (
                        time.time() - self.start_time
                        if hasattr(self, "start_time")
                        else 0
                    ),
                }
            }

        @self.app.get("/stats")
        async def stats():
            """详细统计信息"""
            return await subscription_manager.get_subscription_stats()

    async def startup(self):
        """应用启动逻辑"""
        self.start_time = time.time()
        logger.info("VabHub GraphQL API started")

    async def shutdown(self):
        """应用关闭逻辑"""
        logger.info("VabHub GraphQL API shutting down")


# 创建GraphQL应用实例
def create_graphql_app(config: Config = None) -> VabHubGraphQLApp:
    """创建GraphQL应用实例"""
    if config is None:
        config = get_config_by_env()

    return VabHubGraphQLApp(config)


# 全局GraphQL应用实例
graphql_app = create_graphql_app()
