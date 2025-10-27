#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket实时通信系统
支持实时进度更新和日志推送
"""

import asyncio
import json
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect
from core.event import event_manager, Event, EventType
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket):
        """连接WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {
            'connected_at': asyncio.get_event_loop().time(),
            'last_activity': asyncio.get_event_loop().time()
        }
        logger.info("WebSocket连接建立", client_count=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_data:
            del self.connection_data[websocket]
        logger.info("WebSocket连接断开", client_count=len(self.active_connections))
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(message)
            self.connection_data[websocket]['last_activity'] = asyncio.get_event_loop().time()
        except Exception as e:
            logger.error("发送个人消息失败", error=str(e))
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """广播消息给所有连接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                self.connection_data[connection]['last_activity'] = asyncio.get_event_loop().time()
            except Exception as e:
                logger.error("广播消息失败", error=str(e))
                disconnected.append(connection)
        
        # 清理断开连接
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_json(self, data: Dict[str, Any]):
        """发送JSON数据"""
        await self.broadcast(json.dumps(data))
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        return {
            'active_connections': len(self.active_connections),
            'connections': [
                {
                    'connected_at': data['connected_at'],
                    'last_activity': data['last_activity']
                }
                for data in self.connection_data.values()
            ]
        }


class WebSocketHandler:
    """WebSocket处理器"""
    
    def __init__(self):
        self.manager = ConnectionManager()
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """设置事件处理器"""
        # 注册事件监听器
        event_manager.subscribe(EventType.FILE_SCAN_STARTED, self.on_file_scan_started)
        event_manager.subscribe(EventType.FILE_SCAN_COMPLETED, self.on_file_scan_completed)
        event_manager.subscribe(EventType.FILE_PROCESSING_STARTED, self.on_file_processing_started)
        event_manager.subscribe(EventType.FILE_PROCESSING_COMPLETED, self.on_file_processing_completed)
        event_manager.subscribe(EventType.FILE_RENAMED, self.on_file_renamed)
        event_manager.subscribe(EventType.ERROR_OCCURRED, self.on_error_occurred)
    
    async def handle_websocket(self, websocket: WebSocket):
        """处理WebSocket连接"""
        await self.manager.connect(websocket)
        
        try:
            # 发送连接成功消息
            await self.manager.send_personal_message(json.dumps({
                'type': 'connection_established',
                'message': 'WebSocket连接成功',
                'timestamp': asyncio.get_event_loop().time()
            }), websocket)
            
            # 监听客户端消息
            while True:
                data = await websocket.receive_text()
                await self.handle_client_message(websocket, data)
                
        except WebSocketDisconnect:
            self.manager.disconnect(websocket)
        except Exception as e:
            logger.error("WebSocket处理异常", error=str(e))
            self.manager.disconnect(websocket)
    
    async def handle_client_message(self, websocket: WebSocket, message: str):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'ping':
                # 响应ping
                await self.manager.send_personal_message(json.dumps({
                    'type': 'pong',
                    'timestamp': asyncio.get_event_loop().time()
                }), websocket)
            
            elif message_type == 'get_status':
                # 获取状态
                await self.send_status_update(websocket)
            
            elif message_type == 'subscribe':
                # 订阅特定事件
                channels = data.get('channels', [])
                await self.handle_subscription(websocket, channels)
            
            else:
                logger.warning("未知的WebSocket消息类型", message_type=message_type)
                
        except json.JSONDecodeError:
            logger.warning("WebSocket消息JSON解析失败", message=message)
        except Exception as e:
            logger.error("处理WebSocket消息失败", error=str(e))
    
    async def send_status_update(self, websocket: WebSocket):
        """发送状态更新"""
        # 这里可以发送当前处理状态等信息
        status_data = {
            'type': 'status_update',
            'timestamp': asyncio.get_event_loop().time(),
            'active_connections': len(self.manager.active_connections),
            'message': '系统运行正常'
        }
        await self.manager.send_personal_message(json.dumps(status_data), websocket)
    
    async def handle_subscription(self, websocket: WebSocket, channels: List[str]):
        """处理订阅"""
        # 记录订阅信息
        if websocket in self.manager.connection_data:
            self.manager.connection_data[websocket]['subscriptions'] = channels
        
        await self.manager.send_personal_message(json.dumps({
            'type': 'subscription_confirmed',
            'channels': channels,
            'timestamp': asyncio.get_event_loop().time()
        }), websocket)
    
    # 事件处理器方法
    def on_file_scan_started(self, event: Event):
        """文件扫描开始事件"""
        asyncio.create_task(self.manager.send_json({
            'type': 'file_scan_started',
            'data': event.data,
            'timestamp': asyncio.get_event_loop().time()
        }))
    
    def on_file_scan_completed(self, event: Event):
        """文件扫描完成事件"""
        asyncio.create_task(self.manager.send_json({
            'type': 'file_scan_completed',
            'data': event.data,
            'timestamp': asyncio.get_event_loop().time()
        }))
    
    def on_file_processing_started(self, event: Event):
        """文件处理开始事件"""
        asyncio.create_task(self.manager.send_json({
            'type': 'file_processing_started',
            'data': event.data,
            'timestamp': asyncio.get_event_loop().time()
        }))
    
    def on_file_processing_completed(self, event: Event):
        """文件处理完成事件"""
        asyncio.create_task(self.manager.send_json({
            'type': 'file_processing_completed',
            'data': event.data,
            'timestamp': asyncio.get_event_loop().time()
        }))
    
    def on_file_renamed(self, event: Event):
        """文件重命名事件"""
        asyncio.create_task(self.manager.send_json({
            'type': 'file_renamed',
            'data': {
                'file_path': event.file_path,
                'original_name': event.original_name,
                'new_name': event.new_name,
                'media_type': event.media_type
            },
            'timestamp': asyncio.get_event_loop().time()
        }))
    
    def on_error_occurred(self, event: Event):
        """错误事件"""
        asyncio.create_task(self.manager.send_json({
            'type': 'error_occurred',
            'data': event.data,
            'timestamp': asyncio.get_event_loop().time()
        }))


# 全局WebSocket处理器实例
websocket_handler = WebSocketHandler()