import hashlib
import secrets
import random
import smtplib
from email.mime.text import MIMEText


def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def send_otp_email(to_email: str, otp: str) -> None:
    sender = os.getenv("EMAIL_USER")
    app_password = os.getenv("EMAIL_APP_PASSWORD")

    msg = MIMEText(f"Your verification code is: {otp}\n\nThis code expires in 10 minutes.")
    msg["Subject"] = "Verify your email"
    msg["From"] = sender
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, app_password)
        server.sendmail(sender, to_email, msg.as_string())
 
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