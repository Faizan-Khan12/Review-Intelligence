"""Supabase token verification service with lightweight caching."""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from loguru import logger


class SupabaseAuthService:
    """Validate Supabase access tokens by querying GoTrue user endpoint."""

    def __init__(self) -> None:
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        self.timeout_seconds = float(os.getenv("SUPABASE_AUTH_TIMEOUT_SECONDS", "5"))
        self.cache_ttl_seconds = int(os.getenv("SUPABASE_AUTH_CACHE_TTL_SECONDS", "60"))
        self.enabled = bool(self.supabase_url and self.supabase_anon_key)
        self._token_cache: Dict[str, Dict[str, Any]] = {}

        if not self.enabled:
            logger.info("Supabase auth disabled (SUPABASE_URL/SUPABASE_ANON_KEY missing)")

    def _cache_get(self, token: str) -> Optional[Dict[str, Any]]:
        cached = self._token_cache.get(token)
        if not cached:
            return None
        if cached["expires_at"] <= time.time():
            self._token_cache.pop(token, None)
            return None
        return cached.get("principal")

    def _cache_set(self, token: str, principal: Dict[str, Any]) -> None:
        self._token_cache[token] = {
            "principal": principal,
            "expires_at": time.time() + max(1, self.cache_ttl_seconds),
        }

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _to_principal(self, user_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user_id = user_payload.get("id")
        email = user_payload.get("email")
        if not user_id or not email:
            return None

        app_metadata = user_payload.get("app_metadata") or {}
        user_metadata = user_payload.get("user_metadata") or {}
        role = app_metadata.get("role") or user_metadata.get("role") or "user"

        email_verified_at = (
            user_payload.get("email_confirmed_at")
            or user_payload.get("confirmed_at")
            or user_payload.get("phone_confirmed_at")
        )

        principal = {
            "id": str(user_id),
            "email": str(email).lower(),
            "role": str(role),
            "is_active": True,
            "email_verified_at": self._parse_dt(email_verified_at),
            "provider": "supabase",
            "raw": user_payload,
        }
        return principal

    def get_principal_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Resolve app principal from Supabase access token."""
        token = (token or "").strip()
        if not token or not self.enabled:
            return None

        cached = self._cache_get(token)
        if cached:
            return cached

        user_url = f"{self.supabase_url}/auth/v1/user"
        headers = {
            "apikey": self.supabase_anon_key,
            "Authorization": f"Bearer {token}",
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(user_url, headers=headers)
            if response.status_code != 200:
                return None

            payload = response.json()
            principal = self._to_principal(payload)
            if principal:
                self._cache_set(token, principal)
            return principal
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Supabase token verification failed: {}", str(exc))
            return None


supabase_auth_service = SupabaseAuthService()
