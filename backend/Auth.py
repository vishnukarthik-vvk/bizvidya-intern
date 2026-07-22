import hashlib
import secrets
 
 
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