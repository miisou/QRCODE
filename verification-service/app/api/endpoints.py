from fastapi import APIRouter, HTTPException, status
from app.api.models import InitSessionRequest, InitSessionResponse, VerifyTokenRequest, VerifyTokenResponse
from app.services.session_manager import session_manager
from app.services.whitelist_checker import whitelist_checker
from app.core.config import settings
import time
from datetime import datetime

router = APIRouter()

@router.post("/session/init", response_model=InitSessionResponse, status_code=status.HTTP_201_CREATED)
def init_session(request: InitSessionRequest):
    nonce = session_manager.create_session(str(request.url))
    # In a real app, qr_payload would be a custom scheme or a URL to the web/mobile app handler.
    # Plan says: "myapp://verify?token=..."
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
        # Should we delete? The plan says "Update status EXPIRED" implicitly or explicitly delete.
        # But if we return 404 next time, effectively same.
        # Let's return EXPIRED verdict or HTTP error?
        # Plan: "Удалить сессию, вернуть статус EXPIRED." (This implies a response with status or error)
        # But VerifyTokenResponse has 'verdict'. Let's follow plan's step 3 logic strictly?
        # "Если TTL > 30 -> Удалить сессию, вернуть статус EXPIRED."
        # Note: Response model verdict enum is TRUSTED, UNSAFE, ERROR. NO EXPIRED in Enum!
        # Let's return ERROR or create a new internal status?
        # Re-reading plan:
        # "3. Проверка 2 (TTL)... Удалить сессию, вернуть статус EXPIRED."
        # "4. Проверка 3 (Повтор)... Ошибка 409 Conflict."
        # "Result types: TRUSTED, UNSAFE, ERROR".
        # Maybe EXPIRED is a generic 400 or special JSON?
        # Let's map EXPIRED to ERROR or 400.
        # Let's raise 410 Gone for expired or strict 400.
        # Or return verdict="ERROR" and checked_url="Session Expired"
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
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
