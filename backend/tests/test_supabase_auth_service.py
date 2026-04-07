from datetime import datetime, timezone

from app.services.supabase_auth_service import SupabaseAuthService


def test_to_principal_maps_core_fields():
    service = SupabaseAuthService()
    payload = {
        "id": "user-123",
        "email": "USER@Example.com",
        "email_confirmed_at": "2026-04-06T08:00:00Z",
        "app_metadata": {"role": "admin"},
    }

    principal = service._to_principal(payload)

    assert principal is not None
    assert principal["id"] == "user-123"
    assert principal["email"] == "user@example.com"
    assert principal["role"] == "admin"
    assert principal["is_active"] is True
    assert principal["email_verified_at"] == datetime(2026, 4, 6, 8, 0, tzinfo=timezone.utc)


def test_get_principal_from_token_returns_cached_without_network():
    service = SupabaseAuthService()
    service.enabled = True
    token = "token-abc"
    cached_principal = {"id": "u1", "email": "u1@example.com", "role": "user"}
    service._cache_set(token, cached_principal)

    principal = service.get_principal_from_token(token)

    assert principal == cached_principal


def test_get_principal_from_token_disabled_returns_none():
    service = SupabaseAuthService()
    service.enabled = False

    assert service.get_principal_from_token("any-token") is None
