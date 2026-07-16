import logging
from typing import List
from fastapi import APIRouter, Request, Depends, HTTPException, status

from backend.app.models import PlainLanguageAlert
from backend.app.auth import get_current_staff_user
from backend.app.middleware.rate_limit import staff_limiter
from backend.app.services.alert_service import get_staff_alerts

logger = logging.getLogger("routers.alerts")

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])

@router.get("/alerts", response_model=List[PlainLanguageAlert])
def read_staff_alerts(
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

    try:
        return get_staff_alerts()
    except Exception as e:
        logger.error(f"Error in read_staff_alerts: {e}")
        raise HTTPException(status_code=500, detail="Database connection error while retrieving alerts.")
