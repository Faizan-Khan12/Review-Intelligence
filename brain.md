# BRAIN.md

## 1) Purpose
Canonical, up-to-date context for this repository.
This file should reflect the **current runtime reality**, not historical snapshots.

Last updated: `2026-04-01`

---

## 2) Runtime Truth

### Backend
- Active entrypoint: `backend/main.py`
- Startup command: `uvicorn main:app --host 0.0.0.0 --port 8000`
- Main API behavior is implemented directly in `main.py` (not via router includes).

### Frontend
- Active app page: `frontend/app/page.tsx`
- Main orchestrator: `frontend/components/Dashboard.tsx`
- Backend integration: `frontend/lib/api.ts`

---

## 3) Current Implemented Backend Features

### 3.1 Analyze Pipeline
- Endpoint: `POST /api/v1/analyze`
- Input: `asin`, optional `country`, `max_reviews`, `enable_ai`
- Flow:
  1. Auth check (session cookie)
  2. Cache lookup
  3. Fetch reviews (Apify or mock fallback)
  4. Optional AI/NLP enrichment
  5. Return flat analysis payload

### 3.2 Cache
- Service: `backend/app/services/cache_service.py`
- Key policy: `analysis:{asin}:{country}:{max_reviews}:{enable_ai}`
- Scope: shared/global per request parameters (not user-scoped)
- Env-controlled:
  - `ENABLE_CACHE`
  - `REDIS_URL`
  - `REDIS_TTL_SECONDS`
- Graceful fallback if Redis unavailable.

### 3.3 Auth (Session Cookie)
- Endpoints:
  - `POST /api/v1/auth/signup`
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/auth/me`
- Security utilities: `backend/app/core/security.py`
- Auth service: `backend/app/services/auth_service.py`
- Cookie behavior:
  - `HttpOnly`
  - `SameSite=lax`
  - `Secure=True` in production
  - TTL from `SESSION_TTL_HOURS`

### 3.4 Protected Endpoints
Session auth required for:
- `POST /api/v1/analyze`
- `POST /api/v1/export/csv`
- `POST /api/v1/export/pdf`

Public:
- `GET /`
- `GET /health`
- `GET /api/v1/growth/{asin}`
- `POST /api/v1/insights`

### 3.5 Export
- CSV endpoint currently uses exporter path that can output spreadsheet-style file (historical API naming retained).
- PDF export hardened for cases where `sentiment_distribution` is `None`.

---

## 4) Database and Migrations

### 4.1 ORM Foundation
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/db/__init__.py`

### 4.2 Models
- `users` (`backend/app/models/user.py`)
- `user_sessions` (`backend/app/models/user_session.py`)
- `subscriptions` (`backend/app/models/subscription.py`)

### 4.3 Alembic
- Config: `backend/alembic.ini`
- Env: `backend/alembic/env.py`
- Initial migration:
  - `backend/alembic/versions/775759117711_create_auth_and_subscription_tables.py`

### 4.4 Subscription-Ready Baseline
`subscriptions` includes:
- `provider`
- `provider_customer_id`
- `provider_subscription_id`
- `plan_code`
- `status`
- `current_period_end`

Signup currently creates a placeholder row (`provider=razorpay`, `status=inactive`).
No checkout/webhook/payment logic yet.

---

## 5) Environment Variables (Active)

### Backend
Core:
- `APP_NAME`, `APP_VERSION`, `ENVIRONMENT`, `DEBUG`
- `HOST`, `PORT`, `ALLOWED_ORIGINS`

Data/AI:
- `APIFY_API_TOKEN`, `APIFY_ACTOR_ID`
- `ENABLE_AI`, `MAX_REVIEWS_PER_REQUEST`, `USE_MOCK_FALLBACK`

DB/cache/auth:
- `DATABASE_URL`, `USE_DATABASE`
- `REDIS_URL`, `REDIS_TTL_SECONDS`, `ENABLE_CACHE`
- `SESSION_COOKIE_NAME`, `SESSION_TTL_HOURS`, `COOKIE_SECURE`
- `SECRET_KEY`

### Frontend
- `NEXT_PUBLIC_API_URL`

Primary env templates:
- `backend/.env.example`
- `.env.example` (root)

---

## 6) Validation Status (`2026-04-01`)

Validated via local runtime checks (TestClient + direct calls):
- Auth lifecycle: signup -> me -> logout -> me(401) -> login -> me
- Authorization gates: unauthenticated analyze/export return `401`
- Cache behavior: miss -> hit -> TTL expiry -> miss
- Response shape regression: analyze payload keys intact
- Export smoke tests:
  - authenticated CSV export `200`
  - authenticated PDF export `200`

---

## 7) Current Risks / Debt
1. `backend/main.py` remains large and monolithic.
2. API naming mismatch remains (`/export/csv` route with spreadsheet-style output path).
3. Multiple deployment manifests still exist with potential drift (`render.yaml`, `backend/Render.yaml`, compose files, Fly config).
4. No full automated test suite committed yet for new auth/cache flows.

---

## 8) Next Priority (After Current Work)
1. Subscription implementation (Razorpay):
   - create plan model/limits
   - checkout creation endpoint
   - webhook verification + status sync
   - entitlement checks tied to protected endpoints
2. Add focused backend tests for auth/cache/export regressions.
3. Optional refactor: split `main.py` into routers/services while preserving current behavior.

---

## 9) Change Log (2026-04-01)
- Step 1: runtime/entrypoint wiring fixed.
- Step 2: DB/cache/auth dependencies added.
- Step 3: SQLAlchemy + Alembic + base auth/subscription schema added.
- Step 4: Redis cache service added.
- Step 5: Analyze endpoint read-through caching added.
- Step 6: Session-cookie auth implemented.
- Step 7: Analyze/export endpoints protected.
- Step 8: Subscription placeholders confirmed and wired on signup.
- Step 9: Env/docs updated.
- Step 10: Consolidated validation completed.
- Cleanup pass: `ReadME.md` and `brain.md` rewritten to remove stale historical/runtime references and reflect current source-of-truth behavior.
- Hotfix: frontend auth integration added so protected backend endpoints are usable from UI:
  - `frontend/lib/api.ts` now uses `withCredentials: true` and exposes `signup/login/logout/getCurrentUser`.
  - `frontend/components/Dashboard.tsx` now includes login/signup UI gate + logout action.
  - export requests now send cookies via `credentials: 'include'`.
- Hotfix: authentication hardened + cache inspection UX added:
  - backend cookie SameSite made configurable via `COOKIE_SAMESITE` (production-safe default behavior).
  - added protected endpoint `GET /api/v1/cache/results` for viewing recent cached analyses.
  - frontend dashboard now includes “Cached Results” loader and open-from-cache action.
  - signup flow now includes confirm-password validation on UI.
  - backend signup now validates email format (server-side).
