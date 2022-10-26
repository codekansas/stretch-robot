import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = r = APIRouter()


@r.websocket("/ws")
async def get_ping(ws: WebSocket) -> None:
    await ws.accept()

    try:
        while True:
            await ws.send_json(await ws.receive_json())

    except WebSocketDisconnect:
        logger.exception("Web socket is disconnected")
