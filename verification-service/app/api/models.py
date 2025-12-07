from pydantic import BaseModel
from typing import Literal, List, Dict, Any, Optional

class InitSessionRequest(BaseModel):
    pass  # URL is now expected in headers


class InitSessionResponse(BaseModel):
    nonce: str
    expires_in: int
    qr_payload: str

class VerifyTokenRequest(BaseModel):
    token: str

class VerifyTokenResponse(BaseModel):
    verdict: Literal["TRUSTED", "CAUTION", "UNSAFE", "ERROR"]
    checked_url: str | None = None
    timestamp: str | None = None
    client_ip: str | None = None
    user_agent: str | None = None
    device_os: str | None = None
    device_browser: str | None = None
    device_brand: str | None = None
    is_mobile: Optional[bool] = None
    trust_score: int | None = None
    logs: List[str] | None = None
    details: Dict[str, Any] | None = None

class PollSessionResponse(BaseModel):
    status: Literal["PENDING", "CONSUMED", "EXPIRED"]
    result: VerifyTokenResponse | None = None

class BluetoothData(BaseModel):
    ble_uuid: str
    found: bool = False
    timestamp: str
    supported: bool = True  # Whether BT is supported by browser
