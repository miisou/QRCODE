from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
import fastapi
from app.api.models import InitSessionRequest, InitSessionResponse, VerifyTokenRequest, VerifyTokenResponse
from app.services.session_manager import session_manager
from app.services.websocket_manager import websocket_manager
from app.core.config import settings
import time
from datetime import datetime
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
router = APIRouter()

from app.core.rate_limit import RateLimiter

# Initialize limiters (e.g. 10/min per IP for init, 30/min for verify)
init_limiter = RateLimiter(requests_per_minute=20)
verify_limiter = RateLimiter(requests_per_minute=60)
proximity_limiter = RateLimiter(requests_per_minute=30)
poll_limiter = RateLimiter(requests_per_minute=120)

@router.post("/session/init", response_model=InitSessionResponse)
async def init_session(request: Request, body: InitSessionRequest):
    # Rate Limit by IP
    client_ip = request.client.host if request.client else "unknown"
    init_limiter.check(f"init:{client_ip}")

    # Get Client URL from header
    client_url = request.headers.get("X-Client-Url")
    if not client_url:
        raise HTTPException(status_code=422, detail="Missing X-Client-Url header")
    
    # Validate URL format and security
    try:
        from urllib.parse import urlparse
        parsed = urlparse(client_url)
        
        # Validate scheme (only http/https allowed)
        if parsed.scheme not in ("http", "https"):
            raise HTTPException(status_code=422, detail="Invalid URL scheme. Only http/https allowed")
        
        # Validate URL length (prevent DoS)
        if len(client_url) > 2048:
            raise HTTPException(status_code=422, detail="URL too long (max 2048 characters)")
        
        # Validate hostname exists
        if not parsed.netloc:
            raise HTTPException(status_code=422, detail="Invalid URL: missing hostname")
        
        # Block internal/private IPs (SSRF protection)
        #hostname = parsed.netloc.split(':')[0]  # Remove port if present
        #if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            #raise HTTPException(status_code=422, detail="Invalid URL: localhost not allowed")
        
        # Block private IP ranges (basic check)
        #if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172.16."):
            #raise HTTPException(status_code=422, detail="Invalid URL: private IP ranges not allowed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        raise HTTPException(status_code=422, detail="Invalid URL format")

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
            # Prefer BLE UUID as WebSocket channel key; fall back to nonce if absent
            ble_uuid = bluetooth_data.get("ble_uuid")
            channel_key = ble_uuid
            await websocket_manager.send_verification_success(
                channel_key,
                response_data.model_dump()
            )
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")

    return response_data

from app.api.models import PollSessionResponse

@router.get("/session/poll/{nonce}", response_model=PollSessionResponse)
def poll_session(nonce: str, request: Request):
    # Rate Limit by IP
    client_ip = request.client.host if request.client else "unknown"
    poll_limiter.check(f"poll:{client_ip}")
    
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
async def confirm_proximity(nonce: str, bluetooth_data: BluetoothData, request: Request):
    """
    Confirm BLE proximity detection from browser.
    Stores proximity confirmation in session for verification engine.
    """
    # Rate Limit by IP
    client_ip = request.client.host if request.client else "unknown"
    proximity_limiter.check(f"proximity:{client_ip}")
    
    # Validate nonce format (basic check)
    if len(nonce) > 100 or not nonce.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=422, detail="Invalid nonce format")
    
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
    logger.info(f"Proximity stored for nonce={nonce}, ble_uuid={bluetooth_data.ble_uuid}, supported={bluetooth_data.supported}, found={bluetooth_data.found}")
    
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
    # Validate nonce format (basic check)
    if len(nonce) > 100 or not nonce.replace("-", "").replace("_", "").isalnum():
        await websocket.close(code=1008, reason="Invalid nonce format")
        return
    
    # Verify session exists before accepting connection
    session = session_manager.get_session(nonce)
    if not session or session.get("status") == "EXPIRED":
        await websocket.close(code=1008, reason="Session not found or expired")
        return

    # Ensure WebSocket is opened from the *phone* that scanned the QR, not the web browser (PC)
    # We approximate this by blocking connections from the same IP as the original web client,
    # unless TEST mode is enabled (for local/dev/testing where both run on one host).
    web_client_ip = session.get("ip")
    ws_client_ip = websocket.client.host if websocket.client else None
    if (
        not getattr(settings, "TEST", False)
        and web_client_ip
        and ws_client_ip
        and web_client_ip == ws_client_ip
    ):
        logger.warning(
            f"Blocking WebSocket for nonce={nonce}: ws_client_ip={ws_client_ip} "
            f"matches web_client_ip={web_client_ip} (expected mobile device, not PC)"
        )
        await websocket.close(code=1008, reason="WebSocket must be opened from mobile device")
        return

    # Determine WebSocket channel key:
    # Prefer BLE UUID (so phone connects by UUID), otherwise fall back to nonce.
    proximity = session.get("proximity") or {}
    ble_uuid = proximity.get("ble_uuid")
    # Allow mobile to pass uuid in query string as fallback
    if not ble_uuid:
        ble_uuid = websocket.query_params.get("uuid") if websocket.query_params else None
    channel_key = ble_uuid 

    if not channel_key:
        await websocket.close(code=1008, reason="UUID required for WebSocket")
        return
    
    logger.info(
        f"WebSocket connection attempt for channel_key={channel_key}"
    )
    try:
        await websocket_manager.connect(websocket, channel_key)
        logger.info(f"WebSocket accepted for channel_key={channel_key} (session nonce={nonce})")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket connection for nonce {nonce}: {e}")
        await websocket.close(code=1011, reason="Internal server error")
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
