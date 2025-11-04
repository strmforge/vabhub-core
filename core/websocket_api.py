"""
WebSocket API endpoints for real-time communication
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from .websocket_manager import ConnectionManager, LogBroadcaster

# 创建全局实例
connection_manager = ConnectionManager()
log_broadcaster = LogBroadcaster(connection_manager)

router = APIRouter()


@router.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time logs"""
    await connection_manager.connect(websocket, "logs")

    try:
        while True:
            # Wait for messages from client (optional)
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle client messages if needed
            if message.get("type") == "ping":
                await connection_manager.send_personal_message(
                    {"type": "pong", "timestamp": message.get("timestamp")},
                    websocket,
                )

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, "logs")
    except Exception as e:
        # Log any other errors
        await log_broadcaster.broadcast_log(
            "error", "websocket", f"WebSocket error: {str(e)}"
        )
        connection_manager.disconnect(websocket, "logs")


@router.websocket("/ws/notifications")
async def websocket_notifications_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications"""
    await connection_manager.connect(websocket, "notifications")

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle client messages
            if message.get("type") == "ping":
                await connection_manager.send_personal_message(
                    {"type": "pong", "timestamp": message.get("timestamp")},
                    websocket,
                )

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, "notifications")
    except Exception as e:
        await log_broadcaster.broadcast_log(
            "error", "websocket", f"WebSocket error: {str(e)}"
        )
        connection_manager.disconnect(websocket, "notifications")


@router.websocket("/ws/tasks")
async def websocket_tasks_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time task updates"""
    await connection_manager.connect(websocket, "tasks")

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle client messages
            if message.get("type") == "ping":
                await connection_manager.send_personal_message(
                    {"type": "pong", "timestamp": message.get("timestamp")},
                    websocket,
                )

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, "tasks")
    except Exception as e:
        await log_broadcaster.broadcast_log(
            "error", "websocket", f"WebSocket error: {str(e)}"
        )
        connection_manager.disconnect(websocket, "tasks")
