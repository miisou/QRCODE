from typing import Dict, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections for mobile devices.
    Maps session nonces to WebSocket connections.
    """
    def __init__(self):
        # Map nonce -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, nonce: str):
        """Register a WebSocket connection for a session nonce"""
        await websocket.accept()
        
        if nonce not in self.active_connections:
            self.active_connections[nonce] = set()
        
        self.active_connections[nonce].add(websocket)
        logger.info(f"WebSocket connected for nonce: {nonce}. Total connections for this nonce: {len(self.active_connections[nonce])}")
    
    def disconnect(self, websocket: WebSocket, nonce: str):
        """Remove a WebSocket connection"""
        if nonce in self.active_connections:
            self.active_connections[nonce].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[nonce]:
                del self.active_connections[nonce]
            
            logger.info(f"WebSocket disconnected for nonce: {nonce}")
    
    async def send_verification_success(self, nonce: str, verification_result: dict):
        """
        Send verification success message to all connected clients for this nonce.
        """
        if nonce not in self.active_connections:
            logger.warning(f"No WebSocket connections found for nonce: {nonce}")
            return
        
        message = {
            "type": "verification_success",
            "nonce": nonce,
            "result": verification_result
        }
        
        disconnected = set()
        for websocket in self.active_connections[nonce]:
            try:
                await websocket.send_json(message)
                logger.info(f"Sent verification success to WebSocket for nonce: {nonce}")
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws, nonce)

# Global instance
websocket_manager = WebSocketManager()