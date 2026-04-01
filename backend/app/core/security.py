"""Security utilities for authentication."""

import hashlib
import secrets

from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify plain password against stored hash."""
    return pwd_context.verify(plain_password, password_hash)


def generate_session_token() -> str:
    """Generate a random session token."""
    return secrets.token_urlsafe(48)


def hash_session_token(session_token: str) -> str:
    """Hash session token before storing in DB."""
    return hashlib.sha256(session_token.encode("utf-8")).hexdigest()
