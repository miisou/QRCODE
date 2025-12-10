from fastapi import Request, HTTPException
from app.services.session_manager import session_manager
import time
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60, burst: int = 5):
        self.rpm = requests_per_minute
        self.burst = burst
        self.redis = session_manager.redis

    def check(self, key: str):
        # Redis Key for rate limiting
        # Use Fixed Window for simplicity or Token Bucket. 
        # Let's use simple Fixed Window with expiry
        current_minute = int(time.time() // 60)
        redis_key = f"rate_limit:{key}:{current_minute}"
        
        try:
            # Atomic increment
            # Pipeline for atomicity optional but good practice
            pipe = self.redis.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, 60) # Expire in 60 seconds
            result = pipe.execute()
            
            count = result[0]
            
            if count > self.rpm:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
                
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            # Fail closed for security: if rate limiting fails, block the request
            # This prevents DoS attacks when Redis is unavailable
            logger.error(f"Rate Limit Error: {e}")
            raise HTTPException(status_code=503, detail="Rate limiting service unavailable")

rate_limiter = RateLimiter() # Global instance or dependency
