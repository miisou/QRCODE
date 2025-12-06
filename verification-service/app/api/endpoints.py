from fastapi import APIRouter, HTTPException, status
import fastapi
from app.api.models import InitSessionRequest, InitSessionResponse, VerifyTokenRequest, VerifyTokenResponse
from app.services.session_manager import session_manager
from app.services.whitelist_checker import whitelist_checker
from app.core.config import settings
import time
from datetime import datetime

router = APIRouter()

@router.post("/session/init", response_model=InitSessionResponse, status_code=status.HTTP_201_CREATED)
def init_session(request: fastapi.Request, body: InitSessionRequest):
    # Extract URL from headers
    client_url = request.headers.get("X-Client-Url")
    if not client_url:
        # Fallback logic or error? Detailed plan says "extract headers". 
        # User request: "WC ne sprashivaet url a otpravlyaet svoi v http zagolovke".
        # Let's enforce it or default to something? 
        # Ideally, throw error if missing.
        raise HTTPException(status_code=400, detail="Missing X-Client-Url header")
    
    # Extract Metadata
    user_agent = request.headers.get("User-Agent")
    client_ip = request.client.host if request.client else None

    nonce = session_manager.create_session(client_url, ip=client_ip, ua=user_agent)
    
    return InitSessionResponse(
        nonce=nonce,
        expires_in=settings.SESSION_TTL,
        qr_payload=f"myapp://verify?token={nonce}"
    )

@router.post("/session/verify", response_model=VerifyTokenResponse)
def verify_token(request: VerifyTokenRequest):
    session = session_manager.get_session(request.token)
    
    # 1. Check Existence
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 2. Check TTL
    time_elapsed = time.time() - session["created_at"]
    if time_elapsed > settings.SESSION_TTL:
        raise HTTPException(status_code=410, detail="Session expired")

    # 3. Check Consumed
    if session["status"] == "CONSUMED":
        raise HTTPException(status_code=409, detail="Session already consumed")
    
    # 4. Whitelist Check
    url = session["url"]
    is_trusted = whitelist_checker.is_trusted(url)
    
    # Update status
    session_manager.update_status(request.token, "CONSUMED")
    
    verdict = "TRUSTED" if is_trusted else "UNSAFE"
    
    return VerifyTokenResponse(
        verdict=verdict,
        checked_url=url,
        timestamp=datetime.utcnow().isoformat() + "Z",
        client_ip=session.get("ip"),
        user_agent=session.get("ua")
    )
