"""
WebSocket API endpoints for VabHub Core
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .websocket_manager import websocket_manager

router = APIRouter()


@router.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time logs"""
    await websocket_manager.handle_websocket(websocket, 'logs')


@router.websocket("/ws/notifications")
async def websocket_notifications_endpoint(websocket: WebSocket):
    """WebSocket endpoint for notifications"""
    await websocket_manager.handle_websocket(websocket, 'notifications')


@router.websocket("/ws/system")
async def websocket_system_endpoint(websocket: WebSocket):
    """WebSocket endpoint for system status"""
    await websocket_manager.handle_websocket(websocket, 'system')


@router.get("/ws/status")
async def get_websocket_status():
    """Get WebSocket connection statistics"""
    return {
        "connections": websocket_manager.get_connection_stats(),
        "status": "active"
    }