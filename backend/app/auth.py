import hmac
import datetime
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from backend.app.config import Config

# HTTPBearer auto_error=False allows us to raise a 401 status code instead of a 403 status code when no token is provided.
security_scheme = HTTPBearer(auto_error=False)

class StaffLoginRequest(BaseModel):
    passcode: str = Field(..., description="Staff portal access passcode")

def verify_passcode(passcode: str) -> bool:
    """Compare the provided passcode against STAFF_PASSCODE using hmac.compare_digest to prevent timing attacks."""
    provided_bytes = passcode.encode("utf-8")
    expected_bytes = Config.STAFF_PASSCODE.encode("utf-8")
    return hmac.compare_digest(provided_bytes, expected_bytes)

def create_access_token(data: dict) -> str:
    """Generate a signed JWT token with a 4-hour expiration time."""
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, Config.JWT_SECRET, algorithm="HS256")

def get_current_staff_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> dict:
    """FastAPI dependency to extract and validate the JWT from the Authorization: Bearer <token> header."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        if payload.get("sub") != "staff":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
