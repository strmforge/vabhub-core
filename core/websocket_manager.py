"""
WebSocket Manager for VabHub Core
Provides real-time communication for logs and notifications
"""

import asyncio
import json
from .logging_config import get_logger
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime


class ConnectionManager:
    """管理WebSocket连接"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            'logs': set(),
            'notifications': set(),
            'system': set()
        }
        self.logger = get_logger("vabhub.websocket")
    
    async def connect(self, websocket: WebSocket, channel: str):
        """连接WebSocket到指定频道"""
        await websocket.accept()
        if channel in self.active_connections:
            self.active_connections[channel].add(websocket)
        else:
            self.active_connections[channel] = {websocket}
        
        self.logger.info(f"WebSocket connected to channel '{channel}'")
        
        # 发送连接确认
        await self.send_personal_message({
            'type': 'connection_established',
            'channel': channel,
            'timestamp': datetime.now().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket, channel: str):
        """断开WebSocket连接"""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        self.logger.info(f"WebSocket disconnected from channel '{channel}'")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Failed to send personal message: {e}")
    
    async def broadcast(self, message: Dict[str, Any], channel: str):
        """广播消息到指定频道的所有连接"""
        if channel not in self.active_connections:
            return
        
        disconnected = set()
        for websocket in self.active_connections[channel]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                self.logger.error(f"Failed to broadcast to WebSocket: {e}")
                disconnected.add(websocket)
        
        # 清理断开连接的WebSocket
        for websocket in disconnected:
            self.disconnect(websocket, channel)


class LogBroadcaster:
    """日志广播器"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.logger = get_logger("vabhub.websocket")
    
    async def broadcast_log(self, level: str, source: str, message: str, **kwargs):
        """广播日志消息"""
        log_message = {
            'type': 'log',
            'level': level,
            'source': source,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'id': kwargs.get('id', None),
            'metadata': kwargs.get('metadata', {})
        }
        
        await self.connection_manager.broadcast(log_message, 'logs')
        
        # 如果是错误或警告，也发送到通知频道
        if level in ['error', 'warning']:
            await self.connection_manager.broadcast({
                'type': 'notification',
                'level': level,
                'source': source,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }, 'notifications')
    
    async def broadcast_system_status(self, status: Dict[str, Any]):
        """广播系统状态"""
        system_message = {
            'type': 'system_status',
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        await self.connection_manager.broadcast(system_message, 'system')


class WebSocketManager:
    """WebSocket管理器"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.log_broadcaster = LogBroadcaster(self.connection_manager)
        self.logger = get_logger("vabhub.websocket")
    
    async def handle_websocket(self, websocket: WebSocket, channel: str):
        """处理WebSocket连接"""
        await self.connection_manager.connect(websocket, channel)
        
        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    await self._handle_client_message(message, websocket, channel)
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON received from WebSocket: {data}")
                
        except WebSocketDisconnect:
            self.connection_manager.disconnect(websocket, channel)
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
            self.connection_manager.disconnect(websocket, channel)
    
    async def _handle_client_message(self, message: Dict[str, Any], websocket: WebSocket, channel: str):
        """处理客户端消息"""
        message_type = message.get('type')
        
        if message_type == 'ping':
            # 响应ping消息
            await self.connection_manager.send_personal_message({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            }, websocket)
        
        elif message_type == 'subscribe':
            # 订阅特定类型的消息
            subscription = message.get('subscription', {})
            await self._handle_subscription(subscription, websocket, channel)
        
        elif message_type == 'unsubscribe':
            # 取消订阅
            subscription = message.get('subscription', {})
            await self._handle_unsubscription(subscription, websocket, channel)
        
        else:
            self.logger.warning(f"Unknown message type: {message_type}")
    
    async def _handle_subscription(self, subscription: Dict[str, Any], websocket: WebSocket, channel: str):
        """处理订阅请求"""
        # 这里可以实现更复杂的订阅逻辑
        # 目前只支持简单的频道订阅
        await self.connection_manager.send_personal_message({
            'type': 'subscription_confirmed',
            'channel': channel,
            'timestamp': datetime.now().isoformat()
        }, websocket)
    
    async def _handle_unsubscription(self, subscription: Dict[str, Any], websocket: WebSocket, channel: str):
        """处理取消订阅请求"""
        await self.connection_manager.send_personal_message({
            'type': 'unsubscription_confirmed',
            'channel': channel,
            'timestamp': datetime.now().isoformat()
        }, websocket)
    
    async def broadcast_log(self, level: str, source: str, message: str, **kwargs):
        """广播日志消息"""
        await self.log_broadcaster.broadcast_log(level, source, message, **kwargs)
    
    async def broadcast_system_status(self, status: Dict[str, Any]):
        """广播系统状态"""
        await self.log_broadcaster.broadcast_system_status(status)
    
    def get_connection_stats(self) -> Dict[str, int]:
        """获取连接统计信息"""
        return {
            channel: len(connections)
            for channel, connections in self.active_connections.items()
        }


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()