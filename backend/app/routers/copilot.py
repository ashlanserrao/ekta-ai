import logging
from fastapi import APIRouter, Request, Depends, HTTPException, status

from backend.app.auth import get_current_staff_user
from backend.app.middleware.rate_limit import staff_limiter
from backend.app.services.copilot_service import generate_copilot_report

logger = logging.getLogger("routers.copilot")

router = APIRouter(prefix="/api/v1/staff", tags=["copilot"])


@router.get("/copilot")
def read_copilot(
    req: Request,
    current_user: dict = Depends(get_current_staff_user),
):
    # Rate limiting (shares the staff burst bucket)
    client_ip = req.client.host if req.client else "unknown"
    if staff_limiter.is_rate_limited(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Limit is 30 per 10 seconds.",
        )

    try:
        return generate_copilot_report()
    except Exception as e:
        logger.error(f"Error generating copilot report: {e}")
        raise HTTPException(status_code=500, detail="Unable to generate operations copilot report.")
