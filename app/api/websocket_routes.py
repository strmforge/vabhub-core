#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket API路由
实时通信接口
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket import websocket_handler
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket主端点"""
    await websocket_handler.handle_websocket(websocket)


@router.websocket("/progress")
async def progress_websocket(websocket: WebSocket):
    """进度跟踪WebSocket"""
    await websocket_handler.handle_websocket(websocket)


@router.websocket("/logs")
async def logs_websocket(websocket: WebSocket):
    """日志推送WebSocket"""
    await websocket_handler.handle_websocket(websocket)