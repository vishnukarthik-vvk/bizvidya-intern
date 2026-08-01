import hashlib
import secrets
import random
import smtplib
from email.mime.text import MIMEText
import os
import requests


def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def send_otp_email(to_email: str, otp: str) -> None:
    from_address = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}"},
        json={
            "from": from_address,
            "to": [to_email],
            "subject": "Verify your email",
            "text": f"Your verification code is: {otp}\n\nThis code expires in 10 minutes.",
        },
        timeout=10,
    )
    if not response.ok:
        # surface Resend's actual error instead of a generic 403 traceback
        raise RuntimeError(
            f"Resend API error {response.status_code}: {response.text}"
        )
 
def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with a random salt.
    Stored as 'salt_hex$hash_hex'. Uses only the Python standard library,
    so no extra pip package (bcrypt/passlib) is required.
    """
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
    )
    return f"{salt}${pwd_hash.hex()}"
 
 
def verify_password(password: str, stored: str) -> bool:
    """Verify a plaintext password against a stored 'salt$hash' string."""
    try:
        salt, hash_hex = stored.split("$")
    except (ValueError, AttributeError):
        return False
 
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
    )
    return secrets.compare_digest(pwd_hash.hex(), hash_hex)