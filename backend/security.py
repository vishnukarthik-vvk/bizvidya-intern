"""Authentication, authorisation, PII masking and rate limiting.

Covers tracker rows:
  W6 / Security / Authentication    -> role based authentication
  W6 / Security / Privacy Controls  -> PII masking

Install: pip install "python-jose[cryptography]"
"""

import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
from models.models import User

# ---------------------------------------------------------------- config

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    # Refuse to boot with a default secret — a hardcoded fallback here would let
    # anyone mint tokens for any user_id.
    raise RuntimeError("JWT_SECRET is not set. Generate one: python -c 'import secrets;print(secrets.token_urlsafe(48))'")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MINUTES = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "720"))  # 12h

ROLE_STUDENT = "student"
ROLE_COUNSELLOR = "counsellor"
ROLE_ADMIN = "admin"

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------- tokens

def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role or ROLE_STUDENT,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session expired or invalid, please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------- dependencies

def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="not signed in")
    payload = _decode(creds.credentials)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="account no longer exists")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="please verify your email first")
    return user


def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """For endpoints that behave differently signed-in vs anonymous."""
    if creds is None:
        return None
    try:
        payload = _decode(creds.credentials)
    except HTTPException:
        return None
    return db.query(User).filter(User.id == int(payload["sub"])).first()


def require_role(*allowed: str):
    """Route dependency: `Depends(require_role(ROLE_COUNSELLOR, ROLE_ADMIN))`."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if (user.role or ROLE_STUDENT) not in allowed:
            raise HTTPException(status_code=403, detail="you don't have access to this")
        return user

    return _dep


def authorize_user_id(target_user_id: int, current: User) -> None:
    """Allow a student to touch only their own rows; staff may touch anyone's.

    Call this in every endpoint that still takes a user_id in the path or body.
    Without it those endpoints are an IDOR (see bug B7).
    """
    if current.id == target_user_id:
        return
    if (current.role or ROLE_STUDENT) in (ROLE_COUNSELLOR, ROLE_ADMIN):
        return
    raise HTTPException(status_code=403, detail="you don't have access to this")


# ---------------------------------------------------------------- PII masking

_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
# Indian mobile numbers, with or without +91 / 0 prefix and separators
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?([6-9]\d{4})[\s-]?(\d{5})(?!\d)")
_AADHAAR_RE = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_URL_RE = re.compile(r"https?://\S+")


def mask_pii(text: Optional[str]) -> str:
    """Redact direct identifiers from free text.

    Used on two paths:
      1. anything a student types that gets stored in chat / progress logs
      2. anything shown in the counsellor portal when the student hasn't
         consented to identified sharing

    Deliberately conservative — it over-masks rather than under-masks. It is a
    defence-in-depth layer, not a substitute for access control.
    """
    if not text:
        return ""
    out = _AADHAAR_RE.sub("[aadhaar hidden]", text)
    out = _PAN_RE.sub("[pan hidden]", out)
    out = _EMAIL_RE.sub(r"\1***\2", out)
    out = _PHONE_RE.sub(lambda m: f"{m.group(1)[:2]}***{m.group(2)[-2:]}", out)
    return out


def mask_name(full_name: Optional[str]) -> str:
    """`Yaswanth Kumar` -> `Yaswanth K.` — enough to be useful to a counsellor
    without exposing the full identity in list views."""
    if not full_name:
        return "Student"
    parts = [p for p in full_name.strip().split() if p]
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0].upper()}."


def redact_url(text: str) -> str:
    return _URL_RE.sub("[link removed]", text)


# ---------------------------------------------------------------- rate limiting

_buckets: dict[str, deque] = defaultdict(deque)


def rate_limit(key: str, limit: int, window_seconds: int) -> None:
    """Fixed-window in-process limiter.

    Good enough for a single Render web service. If you scale to more than one
    worker, move this to Redis — each process keeps its own counters.
    """
    now = time.time()
    bucket = _buckets[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=429,
            detail="too many requests, please wait a moment and try again",
        )
    bucket.append(now)


def client_key(request: Request, suffix: str = "") -> str:
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    return f"{ip}:{suffix}"
