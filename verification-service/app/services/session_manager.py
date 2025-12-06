import time
import json
import redis
from typing import Dict, Optional, Literal
from app.core.config import settings
from app.core.security import generate_nonce

class SessionManager:
    def __init__(self):
        # Redis connection
        self.redis = redis.Redis(
            host=settings.REDIS_HOST, 
            port=settings.REDIS_PORT, 
            db=0, 
            decode_responses=True
        )

    def create_session(self, url: str, ip: str = None, ua: str = None) -> str:
        nonce = generate_nonce()
        session_data = {
            "url": url,
            "created_at": time.time(),
            "status": "PENDING",
            "ip": ip,
            "ua": ua,
            # Result stored as JSON string eventually
        }
        # Use simple hash or just JSON string. JSON string with setex is easier for TTL.
        self.redis.setex(
            f"session:{nonce}",
            settings.SESSION_TTL,
            json.dumps(session_data)
        )
        return nonce

    def get_session(self, nonce: str) -> Optional[dict]:
        data = self.redis.get(f"session:{nonce}")        
        if not data:
            return {"status": "EXPIRED"} # Or None, but logic expects object for status check
        
        return json.loads(data)
    
    def update_status(self, nonce: str, status: Literal["CONSUMED"], result: Optional[dict] = None) -> None:
        key = f"session:{nonce}"
        data = self.redis.get(key)
        if data:
            session = json.loads(data)
            session["status"] = status
            if result:
                session["result"] = result
                
            # Update and keep remaining TTL or reset?
            # Usually we keep content but maybe shorten TTL if consumed?
            # Let's just update content and keep same TTL logic (resetting to full TTL or keeping it alive)
            # setex resets TTL. Consumed sessions shouldn't live forever but user needs to see result.
            self.redis.setex(key, settings.SESSION_TTL, json.dumps(session))

session_manager = SessionManager()
