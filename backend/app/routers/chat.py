import logging
from fastapi import APIRouter, Request, Depends, HTTPException, status

from backend.app.models import FanChatRequest, StaffChatRequest, ChatResponse
from backend.app.middleware.rate_limit import chat_limiter, staff_limiter
from backend.app.auth import get_current_staff_user
from backend.app.services.orchestrator import query_stadium_assistant
from backend.app.config import settings

logger = logging.getLogger("routers.chat")

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

@router.post("/fan")
async def chat_fan(request: FanChatRequest, req: Request):
    # Security: Sanitization & Input Validation
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty or only whitespace."
        )
    sanitized_message = request.message.replace("<", "&lt;").replace(">", "&gt;").strip()
    
    # Validate language parameter
    lang = request.language.strip().lower() if request.language else "en"
    if lang not in ["en", "es"]:
        lang = "en"
    
    # Rate Limiting
    client_ip = req.client.host if req.client else "unknown"
    if chat_limiter.is_rate_limited(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Limit is {settings.RATE_LIMIT_LIMIT} per {settings.RATE_LIMIT_WINDOW} seconds."
        )
        
    try:
        history_list = [h.model_dump() for h in request.history] if request.history else []
        accept_header = req.headers.get("accept", "")
        if "text/event-stream" in accept_header:
            from fastapi.responses import StreamingResponse
            from backend.app.services.orchestrator import stream_stadium_assistant
            
            def sse_generator():
                for chunk in stream_stadium_assistant(sanitized_message, is_staff=False, history=history_list):
                    yield f"data: {chunk}\n\n"
            return StreamingResponse(sse_generator(), media_type="text/event-stream")
            
        response_data = query_stadium_assistant(sanitized_message, is_staff=False, history=history_list)
        return response_data
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in chat_fan: {e}")
        raise HTTPException(status_code=500, detail="Internal assistant error.")

@router.post("/staff")
async def chat_staff(
    request: StaffChatRequest,
    req: Request,
    current_user: dict = Depends(get_current_staff_user)
):
    # Rate Limiting
    client_ip = req.client.host if req.client else "unknown"
    if staff_limiter.is_rate_limited(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Limit is 30 per 10 seconds."
        )

    # Security: Sanitization & Input Validation
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty or only whitespace."
        )
    sanitized_message = request.message.replace("<", "&lt;").replace(">", "&gt;").strip()
    
    try:
        history_list = [h.model_dump() for h in request.history] if request.history else []
        accept_header = req.headers.get("accept", "")
        if "text/event-stream" in accept_header:
            from fastapi.responses import StreamingResponse
            from backend.app.services.orchestrator import stream_stadium_assistant
            
            def sse_generator():
                for chunk in stream_stadium_assistant(sanitized_message, is_staff=True, history=history_list):
                    yield f"data: {chunk}\n\n"
            return StreamingResponse(sse_generator(), media_type="text/event-stream")
            
        response_data = query_stadium_assistant(sanitized_message, is_staff=True, history=history_list)
        return response_data
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in chat_staff: {e}")
        raise HTTPException(status_code=500, detail="Internal operations portal error.")
