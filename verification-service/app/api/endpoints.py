from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
import fastapi
from app.api.models import InitSessionRequest, InitSessionResponse, VerifyTokenRequest, VerifyTokenResponse
from app.services.session_manager import session_manager
from app.services.websocket_manager import websocket_manager
from app.core.config import settings
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

from app.core.rate_limit import RateLimiter

# Initialize limiters (e.g. 10/min per IP for init, 30/min for verify)
init_limiter = RateLimiter(requests_per_minute=20)
verify_limiter = RateLimiter(requests_per_minute=60)

@router.post("/session/init", response_model=InitSessionResponse)
async def init_session(request: Request, body: InitSessionRequest):
    # Rate Limit by IP
    client_ip = request.client.host if request.client else "unknown"
    init_limiter.check(f"init:{client_ip}")

    # Get Client URL from header
    client_url = request.headers.get("X-Client-Url")
    if not client_url:
        # For security/MVP we require this, though strictly it should be validated against a list or regex?
        # Let's simple check existence
        # Or maybe it's optional? Plan says "Web Client initiates".
        # If missing, maybe we can't create specific session?
        # Let's trigger 422 if missing as it's crucial for verification context (even if we get it from payload?)
        # Actually payload doesn't have it.
        # Let's raise error.
        raise HTTPException(status_code=422, detail="Missing X-Client-Url header")

    # Capture IP and User-Agent from Request
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    nonce = session_manager.create_session(client_url, ip=client_ip, ua=user_agent)
    
    return InitSessionResponse(
        nonce=nonce,
        expires_in=settings.SESSION_TTL,
        qr_payload=f"myapp://verify?token={nonce}"
    )

@router.post("/session/verify", response_model=VerifyTokenResponse)
async def verify_token(body: VerifyTokenRequest, raw_request: Request, background_tasks: BackgroundTasks):
    request = body # Alias for easier diff
    
    # Rate Limit by IP
    client_ip = raw_request.client.host if raw_request.client else "unknown"
    verify_limiter.check(f"verify:{client_ip}")
    
    # 1. Get Session
    session = session_manager.get_session(request.token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # 2. Check Expiry
    if session["status"] == "EXPIRED":
        raise HTTPException(status_code=410, detail="Session expired")
    
    # 3. Check Consumed
    if session["status"] == "CONSUMED":
        raise HTTPException(status_code=409, detail="Session already consumed")
    
    # 4. Deep Verification
    url = session["url"]
    web_ip = session.get("ip")
    mobile_ip = raw_request.client.host if raw_request.client else None
    bluetooth_data = session.get("proximity")  # Get BLE proximity data
    
    from app.services.verification_engine import verification_engine
    result = verification_engine.verify(url, web_ip=web_ip, mobile_ip=mobile_ip, proximity=bluetooth_data)
    
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
    
    # Send WebSocket notification if verification succeeded and proximity was confirmed
    if result["verdict"] in ["TRUSTED", "CAUTION"] and bluetooth_data and bluetooth_data.get("confirmed"):
        try:
            await websocket_manager.send_verification_success(
                request.token,
                response_data.model_dump()
            )
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")

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

from app.api.models import BluetoothData

@router.post("/session/proximity/{nonce}")
async def confirm_proximity(nonce: str, bluetooth_data: BluetoothData):
    """
    Confirm BLE proximity detection from browser.
    Stores proximity confirmation in session for verification engine.
    """
    session = session_manager.get_session(nonce)
    if not session or session.get("status") == "EXPIRED":
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    # Store proximity data in session
    # If BLE not supported, mark as not confirmed (but verification will pass)
    # If BLE supported and close, mark as confirmed (verification passes)
    # If BLE supported but not close/not found, don't call this endpoint (verification fails)
    session_manager.update_proximity(nonce, {
        "ble_uuid": bluetooth_data.ble_uuid,
        "found": bluetooth_data.found,
        "timestamp": bluetooth_data.timestamp,
        "supported": bluetooth_data.supported,  # Store whether BLE is supported by browser
        "confirmed": bluetooth_data.supported and bluetooth_data.found  # Only confirmed if supported AND found
    })
    
    return {"status": "proximity_confirmed"}

@router.get("/ws/test")
async def websocket_test():
    """Test endpoint to verify WebSocket routes are registered"""
    return {"status": "WebSocket routes are registered", "endpoint": "/api/v1/ws/verification/{nonce}"}

@router.websocket("/ws/verification/{nonce}")
async def websocket_verification(websocket: WebSocket, nonce: str):
    """
    WebSocket endpoint for mobile app to receive verification success notifications.
    Mobile app connects with the session nonce (token) from QR code.
    """
    logger.info(f"WebSocket connection attempt for nonce: {nonce}")
    try:
        await websocket_manager.connect(websocket, nonce)
        logger.info(f"WebSocket accepted for nonce: {nonce}")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket connection for nonce {nonce}: {e}")
        return
    
    try:
        # Keep connection alive and wait for messages
        while True:
            # Optionally handle incoming messages (ping/pong, etc.)
            data = await websocket.receive_text()
            logger.debug(f"Received message from WebSocket for nonce {nonce}: {data}")
            # Echo back or handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, nonce)
        logger.info(f"WebSocket disconnected for nonce: {nonce}")
    except Exception as e:
        logger.error(f"WebSocket error for nonce {nonce}: {e}")
        websocket_manager.disconnect(websocket, nonce)
