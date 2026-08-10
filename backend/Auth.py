

import hashlib
import os
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import requests

PBKDF2_ITERATIONS = 480_000
MAX_OTP_ATTEMPTS = 5

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


# ---------------------------------------------------------------- OTP


def generate_otp() -> str:
    """Cryptographically secure 6-digit code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def send_otp_email(to_email: str, otp: str) -> str:
    from_address = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set")

    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": from_address,
            "to": [to_email],
            "subject": "Verify your email",
            "text": f"Your verification code is: {otp}\n\nThis code expires in 10 minutes.",
        },
        timeout=15,
    )
    if not response.ok:
        raise RuntimeError(f"Resend API error {response.status_code}: {response.text}")
    try:
        return response.json().get("id", "")
    except ValueError:
        return ""


def verify_otp_code(db, email: str, submitted: str) -> Tuple[bool, str]:
    """Check a submitted code against the newest unused OTP for this email.

    Returns (ok, message). Enforces: single use, expiry, and an attempt cap so a
    6-digit code can't be brute-forced inside its 10-minute window.
    """
    from models.models import EmailOTP

    record = (
        db.query(EmailOTP)
        .filter(EmailOTP.email == email, EmailOTP.used.is_(False))
        .order_by(EmailOTP.id.desc())
        .first()
    )
    if not record:
        return False, "no active verification code — request a new one"

    if record.attempts >= MAX_OTP_ATTEMPTS:
        record.used = True
        db.commit()
        return False, "too many incorrect attempts — request a new code"

    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        record.used = True
        db.commit()
        return False, "verification code expired — request a new one"

    record.attempts += 1
    if not secrets.compare_digest(record.otp_code, submitted.strip()):
        db.commit()
        remaining = MAX_OTP_ATTEMPTS - record.attempts
        return False, (
            f"incorrect code — {remaining} attempt{'s' if remaining != 1 else ''} left"
            if remaining > 0
            else "too many incorrect attempts — request a new code"
        )

    record.used = True
    db.commit()
    return True, "verified"


def invalidate_previous_otps(db, email: str) -> None:
    """Called before issuing a new code so only one is ever live."""
    from models.models import EmailOTP

    db.query(EmailOTP).filter(EmailOTP.email == email, EmailOTP.used.is_(False)).update(
        {"used": True}, synchronize_session=False
    )
    db.commit()


# ---------------------------------------------------------------- passwords


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256, stored as 'iterations$salt_hex$hash_hex'.

    The iteration count is stored so it can be raised later without breaking
    existing logins.
    """
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return f"{PBKDF2_ITERATIONS}${salt}${pwd_hash.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    """Verify against both the new 3-part format and the original 2-part one."""
    if not stored:
        return False
    parts = stored.split("$")
    try:
        if len(parts) == 3:
            iterations, salt, hash_hex = int(parts[0]), parts[1], parts[2]
        elif len(parts) == 2:
            iterations, salt, hash_hex = 100_000, parts[0], parts[1]  # legacy rows
        else:
            return False
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
        )
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(pwd_hash.hex(), hash_hex)


def needs_rehash(stored: Optional[str]) -> bool:
    """True for legacy 100k-iteration hashes. Re-hash on next successful login."""
    if not stored:
        return False
    parts = stored.split("$")
    if len(parts) == 2:
        return True
    try:
        return int(parts[0]) < PBKDF2_ITERATIONS
    except (ValueError, IndexError):
        return True


def create_access_token(user) -> str:
    """Signed JWT carrying the claims the frontend's RequireAuth/RequireStaff need."""
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)