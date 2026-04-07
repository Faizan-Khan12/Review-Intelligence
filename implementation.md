# Implementation Plan: Redis + Supabase Auth Migration

## Summary
This document replaces prior implementation notes and is now the canonical plan.

Primary outcomes:
- Use **Supabase Auth** as the source of truth for authentication.
- Keep existing business APIs (`/api/v1/analyze`, `/api/v1/cache/results`, export endpoints) stable.
- Keep Redis caching enabled with a **48-hour TTL** (`REDIS_TTL_SECONDS=172800`).
- Support both local and cloud Redis with the same env contract.

No user migration is required for this phase (single local account; early-stage project).

## Current Status (April 6, 2026)
Completed:
- Added backend Supabase token verification service (`app/services/supabase_auth_service.py`) with short-lived in-memory token cache.
- Protected route auth now enforces Supabase bearer-token auth (`Authorization: Bearer <token>`).
- CSRF checks are disabled for API auth in bearer-token mode.
- Legacy backend auth/admin session routes are deprecated and now return `410 Gone`.
- Frontend auth API now supports Supabase signup/login/logout/refresh and sends bearer token to backend.
- Frontend callback bootstrap now handles:
  - legacy `verify_token` / `reset_token`
  - Supabase callback params (`token_hash`, `type`, `access_token`, `refresh_token`)
- Export API calls now use authenticated `apiClient` so bearer auth works for exports.
- Redis TTL defaults and env examples aligned to 48h (`REDIS_TTL_SECONDS=172800`).
- Added backend tests for Supabase auth principal mapping and cache path.
- Cache service hardened for production debugging:
  - `REDIS_URL` normalization now auto-adds missing scheme (`redis://`) when omitted.
  - Redis connection failure now falls back to in-memory TTL cache (same key format) instead of full no-cache mode.
  - Redis reconnect attempts are throttled (~30s) to avoid repeated connection stalls/log spam.
  - Health/cache responses now expose `cache_backend` and `cache_last_error`.
- ASIN input normalization added:
  - Frontend accepts raw ASIN or full Amazon product URL in both sidebar and quick mobile form.
  - Backend `/api/v1/analyze` now normalizes/validates ASIN from raw input or product URL and returns `400` for invalid input.
- Product title visibility added for analysis discovery:
  - Backend cache listing now returns `product_title` for each cached entry.
  - Frontend cached cards now display product title prominently with ASIN secondary.
  - Main analysis screen now displays product title + ASIN header for currently opened analysis.
- Apify product-name mapping quality improved:
  - Product title extraction is now strict to product-level fields (`productTitle`, `productName`, guarded `name`).
  - Generic `title` keys are excluded from product naming to avoid review titles being treated as product name.
  - Fallback title remains `Product {asin}` when product-level title metadata is absent.
- Summary/rating quality fixes:
  - Frontend detailed and side summary views now use backend `summaries.overall` as primary source.
  - Frontend review rating usage now matches backend (`rating`, with `stars` fallback for compatibility).
  - Backend Apify rating parsing expanded to additional key variants and nested objects.
  - Backend average rating now uses only valid review ratings (>0), with product-level rating fallback when needed.
- Supabase password reset callback handling now supports both delivery formats:
  - `token_hash` recovery links.
  - Recovery session links (`type=recovery` + `access_token`) without `token_hash`.
- Dashboard reset form rendering now prioritizes recovery flow even when Supabase callback also produces an authenticated session.
- Backend email fallback logging was hardened to avoid body/link leakage when SMTP is not configured.
- Repository cleanup completed:
  - Removed stale docs (`brain.md`, `CI-CD-SETUP.md`, `DEPLOYMENT.md`, `OPENAI-SETUP.md`, `PROPERTY-SYNC-CHECKLIST.md`).
  - Kept canonical docs set (`README.md`, `AGENTS.md`, `implementation.md`).
  - Removed duplicate legacy workflow (`.github/workflows/ci-cd.yml`), keeping `.github/workflows/ci.yml`.
- Legacy local-auth cleanup completed:
  - Removed unused local-auth services (`auth_service.py`, `email_service.py`, `rate_limiter.py`).
  - Removed unused local-auth ORM models (`user_session.py`, `email_verification_token.py`, `password_reset_token.py`) and their old test file.
  - `app/services/__init__.py` and `app/models/__init__.py` now export only active runtime modules/entities.
- Deployment/config cleanup completed:
  - Kept `render.yaml` as canonical deployment manifest.
  - Removed stale deployment artifacts (`.dockerignore`, `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `backend/Render.yaml`, `backend/fly.toml`).

## Goals
- Migrate from custom backend session-cookie auth to bearer-token auth backed by Supabase Auth.
- Preserve response payload shapes used by frontend analytics and exports.
- Maintain graceful behavior when Redis is unavailable (fallback to in-memory cache mode).
- Keep India (`IN`) as default analysis region.

Status note:
- Graceful behavior was upgraded from **no-cache fallback** to **memory-cache fallback** for better cost control when cloud Redis is temporarily unreachable.

## Redis Plan (Local + Cloud)
### Runtime Contract
- `ENABLE_CACHE=true`
- `REDIS_URL=<redis-url>`
- `REDIS_TTL_SECONDS=172800`

### Local
- Run Redis locally and use `REDIS_URL=redis://localhost:6379/0`.
- Verify cache hit/miss on repeated analyze requests.

### Cloud
- Prefer Supabase Redis add-on **if available** in target environment.
- If unavailable, use Upstash (or equivalent) with the same `REDIS_URL` variable.
- No code changes should be required when switching providers.
- Important: use the **TCP Redis URL** (`rediss://...`) and not the REST URL/token pair.

## Supabase Auth Migration Plan
### Frontend
- Replace custom auth flows with Supabase SDK auth flows (signup/login/logout/reset/verify).
- Send Supabase access token in `Authorization: Bearer <jwt>` for protected backend calls.
- Remove dependency on CSRF for API auth once backend is fully bearer-token based.

### Backend
- Add auth dependency to validate Supabase JWT for protected routes.
- Replace session-cookie auth checks on protected APIs with bearer-token checks.
- Keep authorization gates (verified email/role) based on Supabase claims or metadata.

### Transition
- Legacy local auth endpoints are now explicitly deprecated (HTTP `410`).
- Supabase bearer token is the only supported auth mechanism for protected API access.

## API/Interface Compatibility
- Keep analyze/cache/export response schemas unchanged.
- Keep `from_cache` behavior unchanged.
- Keep cache key format unchanged:
  - `analysis:{asin}:{country}:{max_reviews}:{enable_ai}`

## Test Plan
1. Auth validation:
- Valid Supabase token -> protected endpoints succeed.
- Missing/invalid/expired token -> deterministic 401/403.

2. Cache validation:
- First analyze request -> `from_cache=false`.
- Repeated identical request -> `from_cache=true`.
- `/api/v1/cache/results` returns cached entry and `cache_enabled=true`.
- Verify `cache_backend` is:
  - `redis` when cloud Redis is connected
  - `memory` when Redis is unavailable (temporary fallback)

3. TTL validation:
- Use short TTL in test env; verify hit before expiry, miss after expiry.

4. Failure-mode validation:
- Redis unavailable -> app still responds with memory-cache fallback mode.

5. Regression checks:
- Frontend type-check passes.
- Backend tests pass.
- Frontend dashboards render unchanged payloads.

## Rollout Steps
1. Finalize env vars and verify Redis behavior locally.
2. Implement Supabase auth in frontend.
3. Implement Supabase JWT verification in backend and switch protected routes.
4. Validate end-to-end auth + analyze + cache flows.
5. Remove legacy auth internals after confidence checks.
6. Update supporting docs (`AGENTS.md`, README auth/caching sections).

## Assumptions
- Supabase Auth migration is mandatory in this phase.
- Supabase Redis availability is environment-dependent; fallback provider is acceptable.
- Default cache TTL remains 48 hours unless explicitly changed.
- Default analysis region remains India (`IN`).
