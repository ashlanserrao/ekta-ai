"""Fan and staff chat endpoints (JSON reply or SSE token stream).

Both endpoints share one pipeline: validate + sanitize the message, rate-limit
by client IP, then either stream tokens (Accept: text/event-stream) or return a
single JSON response. They differ only in auth, the rate-limit bucket, and the
is_staff flag passed to the orchestrator.
"""
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.app.models import FanChatRequest, StaffChatRequest
from backend.app.middleware.rate_limit import chat_limiter, staff_limiter, IPBasedRateLimiter
from backend.app.auth import get_current_staff_user
from backend.app.services.orchestrator import query_stadium_assistant, stream_stadium_assistant
from backend.app.config import settings

logger = logging.getLogger("routers.chat")

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def _sanitize_message(message: str) -> str:
    """Reject empty input and neutralize HTML angle brackets against injection."""
    if not message or not message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty or only whitespace.",
        )
    return message.replace("<", "&lt;").replace(">", "&gt;").strip()


def _enforce_rate_limit(req: Request, limiter: IPBasedRateLimiter, detail: str) -> None:
    client_ip = req.client.host if req.client else "unknown"
    if limiter.is_rate_limited(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


def _respond(message: str, req: Request, is_staff: bool, history: list, error_detail: str):
    """Shared chat pipeline: stream over SSE when requested, else return JSON."""
    try:
        if "text/event-stream" in req.headers.get("accept", ""):
            def sse_generator():
                for chunk in stream_stadium_assistant(message, is_staff=is_staff, history=history):
                    yield f"data: {chunk}\n\n"
            return StreamingResponse(sse_generator(), media_type="text/event-stream")

        return query_stadium_assistant(message, is_staff=is_staff, history=history)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in {'staff' if is_staff else 'fan'} chat: {e}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/fan")
async def chat_fan(request: FanChatRequest, req: Request):
    sanitized_message = _sanitize_message(request.message)
    _enforce_rate_limit(
        req, chat_limiter,
        f"Too many requests. Limit is {settings.RATE_LIMIT_LIMIT} per {settings.RATE_LIMIT_WINDOW} seconds.",
    )
    history = [h.model_dump() for h in request.history] if request.history else []
    return _respond(sanitized_message, req, is_staff=False, history=history,
                    error_detail="Internal assistant error.")


@router.post("/staff")
async def chat_staff(
    request: StaffChatRequest,
    req: Request,
    current_user: dict = Depends(get_current_staff_user),
):
    _enforce_rate_limit(req, staff_limiter, "Too many requests. Limit is 30 per 10 seconds.")
    sanitized_message = _sanitize_message(request.message)
    history = [h.model_dump() for h in request.history] if request.history else []
    return _respond(sanitized_message, req, is_staff=True, history=history,
                    error_detail="Internal operations portal error.")
