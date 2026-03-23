import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional


TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "86400"))
_SECRET = os.getenv("AUTH_TOKEN_SECRET", "socialsphere-dev-secret")


def _urlsafe_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _urlsafe_b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(email: str) -> str:
    now = int(time.time())
    payload = {"sub": email.lower().strip(), "iat": now, "exp": now + TOKEN_TTL_SECONDS}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_part = _urlsafe_b64(payload_bytes)
    signature = hmac.new(_SECRET.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    sig_part = _urlsafe_b64(signature)
    return f"{payload_part}.{sig_part}"


def get_email_from_token(token: str) -> Optional[str]:
    try:
        payload_part, sig_part = token.split(".", 1)
    except ValueError:
        return None

    expected_sig = hmac.new(_SECRET.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    actual_sig = _urlsafe_b64_decode(sig_part)
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None

    try:
        payload = json.loads(_urlsafe_b64_decode(payload_part).decode("utf-8"))
    except Exception:
        return None

    sub = str(payload.get("sub", "")).lower().strip()
    exp = int(payload.get("exp", 0))
    if not sub or exp < int(time.time()):
        return None
    return sub


def get_email_from_auth_header(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    value = authorization.strip()
    if not value.lower().startswith("bearer "):
        return None
    token = value[7:].strip()
    if not token:
        return None
    return get_email_from_token(token)
