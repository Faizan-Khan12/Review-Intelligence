"""Auth service for user and session management."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.subscription import Subscription
from app.models.user import User
from app.models.user_session import UserSession


class AuthService:
    """Authentication and session lifecycle operations."""

    def create_user(self, db: Session, email: str, password: str) -> User:
        """Create a new user account."""
        normalized_email = email.strip().lower()
        existing = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
        if existing:
            raise ValueError("Email is already registered")

        user = User(email=normalized_email, password_hash=hash_password(password), is_active=True)
        db.add(user)
        db.flush()

        # Keep a placeholder subscription row for future billing integration.
        db.add(Subscription(user_id=user.id))
        db.commit()
        db.refresh(user)
        return user

    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """Validate credentials and return user when valid."""
        normalized_email = email.strip().lower()
        user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
        if not user or not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_session(self, db: Session, user_id: int, ttl_hours: int) -> str:
        """Create a new server-side session and return raw token."""
        raw_token = generate_session_token()
        session = UserSession(
            user_id=user_id,
            session_token_hash=hash_session_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
            revoked=False,
        )
        db.add(session)
        db.commit()
        return raw_token

    def get_user_from_session_token(self, db: Session, raw_token: str) -> Optional[User]:
        """Resolve authenticated user from raw session token."""
        token_hash = hash_session_token(raw_token)
        now = datetime.utcnow()

        stmt = (
            select(User)
            .join(UserSession, UserSession.user_id == User.id)
            .where(UserSession.session_token_hash == token_hash)
            .where(UserSession.revoked.is_(False))
            .where(UserSession.expires_at > now)
            .where(User.is_active.is_(True))
        )
        return db.execute(stmt).scalar_one_or_none()

    def revoke_session(self, db: Session, raw_token: str) -> None:
        """Revoke existing session if present."""
        token_hash = hash_session_token(raw_token)
        session = db.execute(
            select(UserSession).where(UserSession.session_token_hash == token_hash)
        ).scalar_one_or_none()
        if not session:
            return
        session.revoked = True
        db.add(session)
        db.commit()


auth_service = AuthService()

