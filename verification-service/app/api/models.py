from pydantic import BaseModel, HttpUrl
from typing import Literal

class InitSessionRequest(BaseModel):
    pass  # URL is now expected in headers


class InitSessionResponse(BaseModel):
    nonce: str
    expires_in: int
    qr_payload: str

class VerifyTokenRequest(BaseModel):
    token: str

class VerifyTokenResponse(BaseModel):
    verdict: Literal["TRUSTED", "UNSAFE", "ERROR"]
    checked_url: str | None = None
    timestamp: str | None = None
    client_ip: str | None = None
    user_agent: str | None = None

