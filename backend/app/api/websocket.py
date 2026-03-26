"""
WebSocket API - 实时推送 PnL, 行情, 策略状态
"""
import asyncio
import json
from datetime import datetime
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])

# 活跃连接集合
active_connections: Set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点

    客户端可发送:
        {"type": "subscribe", "channel": "portfolio"}
        {"type": "subscribe", "channel": "ticker", "symbol": "BTC/USDT"}

    服务端推送:
        {"type": "portfolio", "data": {...}}
        {"type": "ticker", "symbol": "BTC/USDT", "data": {...}}
    """
    await websocket.accept()
    active_connections.add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

            elif msg.get("type") == "subscribe":
                channel = msg.get("channel", "")
                await websocket.send_json({
                    "type": "subscribed",
                    "channel": channel,
                    "message": f"Subscribed to {channel}"
                })

    except WebSocketDisconnect:
        active_connections.discard(websocket)
    except Exception:
        active_connections.discard(websocket)


async def broadcast(message: dict):
    """广播消息到所有连接"""
    disconnected = set()
    for ws in active_connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)
    active_connections -= disconnected
