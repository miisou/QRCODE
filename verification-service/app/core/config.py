import os

class Settings:
    SESSION_TTL: int = 30 # 30 seconds
    PROJECT_NAME: str = "Gov Verify"
    API_V1_STR: str = "/api/v1"
    
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    
    # Allow badssl.com domains for SSL testing when TEST_SSL is True
    TEST_SSL: bool = os.getenv("TEST_SSL", "False").lower() in ("true", "1", "yes")    
    TEST: bool = os.getenv("TEST", "False").lower() in ("true", "1", "yes")    

settings = Settings()
