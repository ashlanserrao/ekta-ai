import logging
from fastapi import APIRouter, HTTPException, status

from backend.app.auth import StaffLoginRequest, verify_passcode, create_access_token

logger = logging.getLogger("routers.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/staff/login")
def staff_login(request: StaffLoginRequest):
    if not verify_passcode(request.passcode):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid passcode"
        )
    token = create_access_token(data={"sub": "staff"})
    return {"token": token}
