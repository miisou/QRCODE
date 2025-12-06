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
    
    # 4. Deep Verification
    url = session["url"]
    from app.services.verification_engine import verification_engine
    result = verification_engine.verify(url)
    
    # Update status MOVED TO END
    # session_manager.update_status(request.token, "CONSUMED")
    
    # Parse User Agent
    ua_string = session.get("ua")
    device_os = None
    device_browser = None
    device_brand = None
    is_mobile = None

    if ua_string:
        try:
            from user_agents import parse
            ua = parse(ua_string)
            device_os = ua.os.family
            device_browser = ua.browser.family
            device_brand = ua.device.brand
            is_mobile = ua.is_mobile
        except:
            pass

    
    response_data = VerifyTokenResponse(
        verdict=result["verdict"],
        checked_url=url,
        timestamp=datetime.utcnow().isoformat() + "Z",
        client_ip=session.get("ip"),
        user_agent=ua_string,
        device_os=device_os,
        device_browser=device_browser,
        device_brand=device_brand,
        is_mobile=is_mobile,
        trust_score=result["score"],
        logs=result["logs"],
        details=result["details"]
    )
    
    # Update status and SAVE RESULT
    session_manager.update_status(request.token, "CONSUMED", response_data.model_dump())

    return response_data

from app.api.models import PollSessionResponse

@router.get("/session/poll/{nonce}", response_model=PollSessionResponse)
def poll_session(nonce: str):
    session = session_manager.get_session(nonce)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    status = session.get("status")
    result = session.get("result")
    
    return PollSessionResponse(
        status=status,
        result=result
    )
