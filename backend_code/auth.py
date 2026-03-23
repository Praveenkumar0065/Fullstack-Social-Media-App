import os
import base64
import hashlib
import hmac
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
PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = max(100_000, int(os.getenv("AUTH_PASSWORD_ITERATIONS", "260000")))


def hash_password(raw_password: str) -> str:
    password = str(raw_password or "")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8").rstrip("=")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt_b64}${digest_b64}"


def _decode_b64_url(data: str) -> bytes:
    padded = data + ("=" * (-len(data) % 4))
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def verify_password(raw_password: str, stored_password: str) -> bool:
    provided = str(raw_password or "")
    stored = str(stored_password or "")
    if not stored:
        return False

    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == PASSWORD_SCHEME:
        try:
            iterations = int(parts[1])
            salt = _decode_b64_url(parts[2])
            expected = _decode_b64_url(parts[3])
        except Exception:
            return False

        derived = hashlib.pbkdf2_hmac("sha256", provided.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(expected, derived)

    # Backward compatibility for existing plaintext credentials.
    return hmac.compare_digest(stored, provided)


def is_password_hashed(stored_password: str) -> bool:
    value = str(stored_password or "")
    return value.startswith(f"{PASSWORD_SCHEME}$")


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
