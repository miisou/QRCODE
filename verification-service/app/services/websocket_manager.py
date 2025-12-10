from typing import Dict, Set
from fastapi import WebSocket
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections for mobile devices.
    Maps logical channel keys (e.g. BLE UUIDs) to WebSocket connections.
    """
    MAX_CONNECTIONS_PER_NONCE = 5  # Limit connections per channel to prevent abuse
    
    def __init__(self):
        # Map channel_key (nonce or BLE UUID) -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, channel_key: str):
        """Register a WebSocket connection for a logical channel (typically BLE UUID)"""

        logger.warning("___________________________________SEEEEEEEEEEEEEEEEEEEEEEEEEEEEX")
        await websocket.accept()
        
        if channel_key not in self.active_connections:
            self.active_connections[channel_key] = set()
        
        # Check connection limit
        if len(self.active_connections[channel_key]) >= self.MAX_CONNECTIONS_PER_NONCE:
            logger.warning(f"Connection limit reached for channel: {channel_key}")
            await websocket.close(code=1008, reason="Too many connections for this session")
            return
        
        self.active_connections[channel_key].add(websocket)
        logger.info(
            f"WebSocket connected for channel: {channel_key}. "
            f"Total connections for this channel: {len(self.active_connections[channel_key])}"
        )
    
    def disconnect(self, websocket: WebSocket, channel_key: str):
        """Remove a WebSocket connection"""
        if channel_key in self.active_connections:
            self.active_connections[channel_key].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[channel_key]:
                del self.active_connections[channel_key]
            
            logger.info(f"WebSocket disconnected for channel: {channel_key}")
    
    async def send_verification_success(self, channel_key: str, verification_result: dict):
        """
        Send verification success message to all connected clients for this channel.
        """
        # Wait up to 3 seconds for a mobile client to connect
        if channel_key not in self.active_connections or not self.active_connections.get(channel_key):
            logger.info(f"No WebSocket yet for channel {channel_key}, waiting up to 3s")
            for _ in range(30):  # 30 * 0.1s = 3s
                await asyncio.sleep(0.1)
                if channel_key in self.active_connections and self.active_connections[channel_key]:
                    break
            else:
                logger.warning(f"No WebSocket connections found for channel: {channel_key} (waited 3s)")
                return
        
        message = {
            "type": "verification_success",
            "channel": channel_key,
            "result": verification_result
        }
        
        # Create a copy of the connections set to avoid RuntimeError if set is modified during iteration
        # This prevents race conditions when disconnect() is called concurrently
        connections_copy = list(self.active_connections[channel_key])
        
        disconnected = set()
        for websocket in connections_copy:
            try:
                await websocket.send_json(message)
                logger.info(f"Sent verification success to WebSocket for channel: {channel_key}")
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws, channel_key)

# Global instance
websocket_manager = WebSocketManager()