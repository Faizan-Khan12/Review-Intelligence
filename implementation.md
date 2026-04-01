# Implementation Plan: Cache + Auth (Subscription-Ready)

## Goal
Reduce API costs with Redis caching, add session-based authentication (signup/login/logout), protect expensive endpoints, and prepare DB schema for Razorpay subscriptions in a later phase.

## Progress
- Step 1: Completed
- Step 2: Completed
- Step 3: Completed
- Step 4: Completed
- Step 5: Completed
- Step 6: Completed
- Step 7: Completed
- Step 8: Completed
- Step 9: Completed
- Step 10: Completed

## Step 1: Stabilize Backend App Wiring (Completed)
1. Confirm single canonical FastAPI app entrypoint.
2. Align compose/runtime command with actual app module.
3. Remove or defer startup commands that depend on not-yet-created migrations.

Completed changes:
- Updated `docker-compose.yml` backend command to run `uvicorn main:app` and removed premature `alembic upgrade head`.
- Fixed script entrypoint in `backend/pyproject.toml` to `ari-server = "main:run_server"`.
- Added `run_server()` in `backend/main.py` and made `__main__` use it.

## Step 2: Add Core Dependencies (Completed)
1. Add backend dependencies for:
   - SQLAlchemy
   - Alembic
   - psycopg2-binary
   - redis (python client)
   - passlib[bcrypt]
2. Keep versions compatible with current FastAPI/Pydantic stack.

Completed changes:
- Added dependency entries in `backend/requirements.txt` for `SQLAlchemy`, `alembic`, `psycopg2-binary`, `redis`, and `passlib[bcrypt]`.
- Added/updated version-bounded dependency entries in `backend/pyproject.toml` for:
  - `SQLAlchemy>=2.0.0,<3.0.0`
  - `alembic>=1.14.0,<2.0.0`
  - `psycopg2-binary>=2.9.0,<3.0.0`
  - `redis>=5.2.0,<6.0.0`
  - `passlib[bcrypt]>=1.7.4,<2.0.0`

## Step 3: Set Up Database + Migration Baseline (Completed)
1. Create SQLAlchemy engine/session setup.
2. Create initial models:
   - users
   - user_sessions
   - subscriptions (placeholder for Razorpay)
3. Initialize Alembic and create first migration.
4. Apply migration in local/dev environment.

Completed changes:
- Initialized Alembic in `backend/alembic/` with config file `backend/alembic.ini`.
- Added DB foundation:
  - `backend/app/db/base.py`
  - `backend/app/db/session.py`
  - `backend/app/db/__init__.py`
- Added models:
  - `backend/app/models/user.py`
  - `backend/app/models/user_session.py`
  - `backend/app/models/subscription.py`
  - `backend/app/models/__init__.py`
- Wired Alembic metadata + DB URL environment support in `backend/alembic/env.py`.
- Created initial migration:
  - `backend/alembic/versions/775759117711_create_auth_and_subscription_tables.py`
- Applied migration locally with:
  - `cd backend && ./venv/bin/alembic upgrade head`
  - Resulting local dev DB file: `backend/dev.db` (tables: `users`, `user_sessions`, `subscriptions`).

## Step 4: Implement Redis Cache Service (Completed)
1. Create cache utility module with:
   - get(key)
   - set(key, value, ttl)
   - delete(key)
2. Wire configuration from env:
   - ENABLE_CACHE
   - REDIS_URL
   - REDIS_TTL_SECONDS
3. Add safe fallback behavior if Redis is unavailable.

Completed changes:
- Added cache service module:
  - `backend/app/services/cache_service.py`
  - Includes `RedisCacheService` with `get`, `set`, `delete`.
- Wired cache service to existing config settings:
  - `ENABLE_CACHE`
  - `REDIS_URL`
  - `REDIS_TTL_SECONDS`
- Added graceful fallback behavior:
  - Returns `None` / `False` on Redis unavailable or disabled mode instead of raising runtime errors.
- Exported cache service from:
  - `backend/app/services/__init__.py`

## Step 5: Add Analyze Response Caching (Completed)
1. Build cache key:
   - `analysis:{asin}:{country}:{max_reviews}:{enable_ai}`
2. In `/api/v1/analyze`:
   - Check cache before Apify call.
   - On hit, return cached response.
   - On miss, run existing flow and cache successful result.
3. Keep response shape unchanged for frontend compatibility.

Completed changes:
- Added cache integration in `backend/main.py`:
  - Cache key helper: `build_analysis_cache_key(asin, country, max_reviews, enable_ai)`.
  - Read-through cache lookup before external fetch in `/api/v1/analyze`.
  - Cache-hit path returns cached payload directly.
  - Cache-miss path performs normal fetch/analysis and caches successful response.
- Implemented approved key format:
  - `analysis:{asin}:{country}:{max_reviews}:{enable_ai}`
  - `enable_ai` normalized to `0/1` in the key.
- Kept response payload structure unchanged for frontend compatibility.
- Added safe no-op fallback in `main.py` if cache service import is unavailable.

## Step 6: Implement Session-Cookie Auth (Completed)
1. Create auth data/service layer:
   - password hashing + verify
   - session token generation
   - hashed session token storage
2. Add endpoints:
   - `POST /api/v1/auth/signup`
   - `POST /api/v1/auth/login`
   - `POST /api/v1/auth/logout`
   - `GET /api/v1/auth/me`
3. Set cookie attributes:
   - HttpOnly
   - SameSite=Lax
   - Secure in production
   - TTL from env

Completed changes:
- Added security utilities in `backend/app/core/security.py`:
  - password hash/verify
  - session token generation
  - session token hashing
- Added auth service layer in `backend/app/services/auth_service.py`:
  - create user
  - authenticate user
  - create/revoke session
  - resolve user from session token
- Added auth endpoints in `backend/main.py`:
  - `POST /api/v1/auth/signup`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/auth/me`
- Added session cookie helpers in `backend/main.py` with:
  - `HttpOnly`
  - `SameSite=lax`
  - `Secure=True` automatically in production
  - TTL from `SESSION_TTL_HOURS`
- Added session config values in `backend/main.py`:
  - `SESSION_COOKIE_NAME`
  - `SESSION_TTL_HOURS`
  - `COOKIE_SECURE`
- Ensured bcrypt compatibility for passlib in dependencies:
  - `backend/requirements.txt` -> `bcrypt<4`
  - `backend/pyproject.toml` -> `bcrypt>=3.2.0,<4.0.0`
- Local runtime validation performed with FastAPI `TestClient`:
  - signup -> me -> logout -> me(401) -> login -> me

## Step 7: Protect Expensive Endpoints
1. Add auth dependency/middleware to resolve current user from session cookie.
2. Protect:
   - `POST /api/v1/analyze`
   - `/api/v1/export/*`
3. Keep `/` and `/health` public.

Completed changes:
- Added `get_current_user(...)` dependency in `backend/main.py` to centralize cookie session auth checks.
- Protected routes with `Depends(get_current_user)`:
  - `POST /api/v1/analyze`
  - `POST /api/v1/export/csv`
  - `POST /api/v1/export/pdf`
- Refactored `GET /api/v1/auth/me` to reuse the same dependency.
- Verified behavior via local TestClient:
  - Unauthenticated analyze/export => `401`
  - Authenticated analyze/export => success responses

## Step 8: Add Subscription-Ready Placeholders
1. Add `subscriptions` table fields for Razorpay mapping:
   - provider
   - provider_customer_id
   - provider_subscription_id
   - plan_code
   - status
   - current_period_end
2. No payment checkout/webhook logic in this phase.

Completed changes:
- Subscription placeholder schema was already implemented in Step 3 migration and model:
  - `backend/app/models/subscription.py`
  - `backend/alembic/versions/775759117711_create_auth_and_subscription_tables.py`
- Placeholder subscription creation on signup was already implemented in Step 6:
  - `backend/app/services/auth_service.py` (`create_user` inserts default subscription row)
- Validation run confirmed:
  - required Razorpay-ready columns exist in `subscriptions` table
  - new user signup creates a placeholder subscription (`provider=razorpay`, `status=inactive`)

## Step 9: Update Environment + Docs
1. Add/confirm env vars in `.env.example`:
   - DATABASE_URL
   - ENABLE_CACHE
   - REDIS_URL
   - REDIS_TTL_SECONDS
   - SESSION_COOKIE_NAME
   - SESSION_TTL_HOURS
   - COOKIE_SECURE
2. Update README with:
   - auth endpoints
   - protected routes
   - caching behavior and key policy

Completed changes:
- Updated backend env template in `backend/.env.example` with explicit values for:
  - `DATABASE_URL`
  - `ENABLE_CACHE`
  - `REDIS_URL`
  - `REDIS_TTL_SECONDS`
  - `SESSION_COOKIE_NAME`
  - `SESSION_TTL_HOURS`
  - `COOKIE_SECURE`
- Updated root env template in `.env.example` with matching DB/cache/session variables.
- Updated docs in `ReadME.md`:
  - Corrected backend runtime command to `uvicorn main:app`.
  - Replaced outdated API paths with current runtime endpoints.
  - Added auth endpoint documentation.
  - Marked protected endpoints (`/api/v1/analyze`, `/api/v1/export/*`).
  - Added Redis caching behavior and key policy documentation.
  - Updated roadmap item for authentication system to completed.

## Step 10: Validation & Testing
1. Cache tests:
   - first call miss, second call hit
   - ttl expiry behavior
2. Auth tests:
   - signup/login/logout/me
   - invalid/expired session handling
3. Authorization tests:
   - unauthenticated analyze/export returns 401
   - authenticated succeeds
4. Regression:
   - verify existing frontend analysis flow still works unchanged.

Completed changes:
- Executed consolidated backend validation (FastAPI `TestClient`) covering:
  - auth flow: signup -> me -> logout -> me(401) -> login
  - authorization: unauthenticated analyze/export return `401`
  - cache behavior: first analyze call miss, second hit, TTL expiry triggers fresh fetch
  - response regression: required analysis response keys are present
- Added export robustness fix in `backend/app/services/exporter.py`:
  - handle `sentiment_distribution=None` safely in PDF export path
  - guard division with `max(total_reviews, 1)` to avoid zero-division
- Validated authenticated export endpoints:
  - `/api/v1/export/csv` -> `200`
  - `/api/v1/export/pdf` -> `200`

---

## Execution Order
1. Step 1-3 (foundation)
2. Step 4-5 (cost reduction via cache)
3. Step 6-7 (auth + protection)
4. Step 8 (subscription-ready schema)
5. Step 9-10 (docs + tests)
