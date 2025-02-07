import logging
from fastapi import WebSocket, WebSocketDisconnect
from typing import List

logger = logging.getLogger("uvicorn.error.websocket")

# Keep track of connected clients
connected_clients: List[WebSocket] = []

async def broadcast_message(message: dict):
    """
    Sends a message to all connected WebSocket clients.
    """
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection handler to communicate with the frontend overlay in real time.
    """
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep WebSocket connection alive
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        connected_clients.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connected_clients.remove(websocket)
