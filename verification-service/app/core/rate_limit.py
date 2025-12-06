from fastapi import Request, HTTPException
from app.services.session_manager import session_manager
import time

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
            # Fail open or closed? Fail open for availability if Redis blips?
            # Creating sessions is critical but abuse is risk. 
            # Let's log and pass if redis fails?
            # Typically fail closed for security, fail open for UX.
            # We already rely on Redis for sessions, so if Redis is down, system is down anyway.
            # So just letting it raise or handling connection error is fine.
            print(f"Rate Limit Error: {e}")
            pass

rate_limiter = RateLimiter() # Global instance or dependency
