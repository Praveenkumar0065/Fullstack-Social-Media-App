import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError


security = HTTPBearer(auto_error=False)
SECRET = os.getenv("AUTH_TOKEN_SECRET", "socialsphere-dev-secret")
ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "86400"))
REFRESH_TTL_SECONDS = int(os.getenv("AUTH_REFRESH_TTL_SECONDS", "604800"))


def create_access_token(subject_email: str, role: str = "user") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject_email.lower().strip(),
        "role": role,
        "jti": uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=TOKEN_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def create_refresh_token(subject_email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject_email.lower().strip(),
        "type": "refresh",
        "jti": uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=REFRESH_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except InvalidTokenError:
        return None

    subject = str(payload.get("sub", "")).lower().strip()
    if not subject:
        return None

    payload["email"] = subject
    return payload


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except InvalidTokenError:
        return None

    if payload.get("type") != "refresh":
        return None

    subject = str(payload.get("sub", "")).lower().strip()
    if not subject:
        return None

    payload["email"] = subject
    return payload


def get_refresh_token_expiry_epoch() -> int:
    now = datetime.now(timezone.utc)
    return int((now + timedelta(seconds=REFRESH_TTL_SECONDS)).timestamp())


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return payload


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if str(user.get("role", "user")) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
