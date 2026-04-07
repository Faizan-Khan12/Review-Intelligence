# Repository Guidelines

## Purpose Of This File
This is the persistent context file for future sessions.  
When token context is lost, start here before touching code.  
After every major implementation, debugging fix, or architecture decision, update this file.

## Current State (Last Updated: April 6, 2026)
- Project: Amazon Review Intelligence (`backend` FastAPI + `frontend` Next.js).
- Auth mode: **Supabase-only** for protected backend APIs.
- Backend protected endpoints require `Authorization: Bearer <access_token>`.
- Legacy local session auth routes were deprecated:
  - Most `/api/v1/auth/*` routes return `410 Gone`.
  - `GET /api/v1/auth/me` is retained for bearer-token introspection.
  - `GET /api/v1/auth/csrf` is retained as a compatibility no-op.
- Legacy local admin auth/session endpoints are deprecated and return `410 Gone`.
- Redis caching is enabled by contract with default TTL 48h (`REDIS_TTL_SECONDS=172800`).
- Default country/region for analysis is `IN` (India) in frontend + backend flows.
- Local `backend/.env` and `frontend/.env.local` now contain Supabase config values (set by operator) and services were restarted/verified.
- Cache service now guards against malformed `REDIS_URL` values (auto-adds `redis://` when omitted).
- Cache runtime is now **Redis-primary with in-memory TTL fallback**:
  - If Redis is unreachable, analyze/cache flows continue using process memory (same key/TTL behavior) instead of no-cache.
  - Redis reconnect attempts are throttled (`~30s`) to avoid repeated slow failures/log spam.
- Cache diagnostics are exposed on API responses (`cache_backend`, `cache_last_error`) to simplify operator debugging.
- Frontend chart warning fixed: `GraphArea` custom `AnimatedBar` no longer forwards Recharts `dataKey` prop to DOM.
- Upstash cloud Redis connectivity is now confirmed in operator dashboard:
  - Analysis keys are being stored remotely.
  - Observed key TTL around `172512`, matching configured 48h TTL decay from `172800`.
- ASIN normalization now accepts either raw ASIN or Amazon product URL:
  - Frontend normalizes URL input before analyze requests.
  - Backend normalizes/validates input again for API safety.
- Cache panel request-noise hardening added in frontend:
  - Prevents parallel duplicate `GET /api/v1/cache/results` requests.
  - Adds short freshness window (~8s) to avoid immediate redundant reloads.
  - API console logging now prints cache-specific fields (`count`, `cache_backend`) for cache endpoint.
- Product-name visibility improved for usability:
  - Main analysis view now shows product title + ASIN header after each analysis.
  - Cached results cards now show product title as primary text and ASIN as secondary metadata.
  - Backend cache list entries now include `product_title` derived from cached payload.
- Apify product-title extraction hardened:
  - Product name now comes only from product-level fields (`productTitle`, `productName`, guarded `name`).
  - Generic row `title` is no longer used for product name (prevents review-title contamination).
  - If missing, fallback remains `Product {asin}`.
- OpenAI/summary wiring and rating robustness improved:
  - OpenAI client is configured and available (`gpt-4o-mini`).
  - Detailed and side summaries now prefer backend `summaries.overall` instead of falling back to generic hardcoded text.
  - Review rating rendering now uses `rating` (with `stars` fallback) to match backend payload.
  - Apify rating parsing now accepts additional rating keys (`ratingScore`, `ratingValue`, `starRating`, nested `reviewRating` object, etc.).
  - Average rating calculation now ignores zero/invalid ratings and falls back to product-level rating when review-level ratings are unavailable.
- Supabase password-recovery callback handling now supports both link formats:
  - `token_hash` recovery links (verify + update password flow).
  - Recovery-session links with `type=recovery` + `access_token` (direct password update flow).
  - Dashboard now prioritizes reset-password UI whenever recovery callback state is present (even if a temporary user session exists).
- Backend email fallback logging was hardened:
  - If SMTP is not configured, backend now logs only metadata (`to`, `subject`) and never logs email body/link content.
- Auth/email audit status (April 6, 2026):
  - Signup/verification/reset delivery is frontend -> Supabase Auth direct.
  - Backend legacy auth email routes are deprecated (`410`) and do not send links.
  - Legacy local-auth modules were removed from active codebase (no runtime path to old session/SMTP auth flow).
- Repository cleanup pass completed (April 6, 2026):
  - Canonical project docs now: `README.md`, `AGENTS.md`, `implementation.md`.
  - Removed stale/duplicative docs: `brain.md`, `CI-CD-SETUP.md`, `DEPLOYMENT.md`, `OPENAI-SETUP.md`, `PROPERTY-SYNC-CHECKLIST.md`.
  - Removed duplicate legacy workflow: `.github/workflows/ci-cd.yml` (kept `.github/workflows/ci.yml`).
  - Deployment/config cleanup:
    - Kept only `render.yaml` as canonical deployment manifest.
    - Removed stale/unused manifests: `.dockerignore`, `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `backend/Render.yaml`, `backend/fly.toml`.
- Frontend design handoff doc added:
  - `frontend.md` now contains a complete Pencil.dev prompt covering all current desktop/mobile screens, states, component inventory, and responsiveness behavior.
  - `frontend.md` was upgraded with an Executive Indigo premium theme system:
    - light/dark design tokens
    - chart palette + sentiment semantics
    - component visual specs, motion, accessibility constraints
    - Pencil deliverables + QA checklist
- `frontend.pen` implementation pass completed on branch `frontend` (April 6, 2026):
  - Executive Indigo visual system is now applied across auth, dashboard, cache panel, and detailed insights screens.
  - Shared UI primitives/tokens were aligned with the Pencil design contract (cards/buttons/inputs/select/tabs/dropdowns/badges/progress).
  - Desktop/mobile sidebar behavior now includes full collapse/drawer close controls aligned with the design frames.
  - Detailed insights export now uses bearer-aware `apiClient` (protected export endpoint compatibility).
  - Detailed insights now includes review sample sections grouped by positive/neutral/negative sentiment.
- UI glitch patch applied after review screenshots (April 6, 2026):
  - Removed navbar export action to eliminate duplicate export controls.
  - Removed top dashboard/detailed user action strips (no duplicate logout controls in main content area).
  - Moved cached-results and logout actions into sidebar footer controls.
  - Removed navbar sidebar-toggle entry point; sidebar access is now through main-screen controls only.
  - Fixed sentiment pie-chart overflow/clipping by removing external pie labels and rendering compact percentage chips below the chart.
- Keyword/theme quality extraction hardening (April 6, 2026):
  - Backend keyword extraction now filters low-value filler words (`great`, `good`, `product`, etc.) and prioritizes high-signal phrases using document frequency + phrase scoring.
  - Backend theme extraction now uses canonical business labels (e.g., `Sound Quality`, `Battery Life`, `Noise Cancellation`) instead of unstable cluster-label combinations.
  - Theme tie-breaking now preserves business-priority order; output avoids labels like `Quality Okay` / `Money Value Money`.
  - Frontend graph rendering now includes a safety filter to suppress low-value legacy keywords/themes from older cached payloads.
- Session handoff (April 6, 2026, end of day):
  - Branch in active use: `frontend` (main branch remains untouched for this redesign work).
  - Current local runtime last verified: frontend `http://localhost:3000`, backend `http://localhost:8000`.
  - Next session focus: visual QA pass on live data/cached data and any remaining auth UX polish.

## Architecture Snapshot
- `backend/main.py`:
  - Primary API runtime.
  - Supabase token principal resolution + auth guards.
  - Analyze endpoint, cache listing, export endpoints.
- `backend/app/services/supabase_auth_service.py`:
  - Validates Supabase tokens via GoTrue `/auth/v1/user`.
  - Includes lightweight in-memory token cache.
- Removed legacy service modules:
  - `backend/app/services/auth_service.py`
  - `backend/app/services/email_service.py`
  - `backend/app/services/rate_limiter.py`
- `backend/app/services/cache_service.py`:
  - Redis read-through cache with automatic memory fallback and retry throttling.
  - Supports diagnostics (`backend`, `last_error`, `memory_entries`).
- `frontend/lib/api.ts`:
  - Supabase auth flows (signup/login/logout/reset/verify).
  - Bearer token injection for backend calls.
  - Callback bootstrap supports both legacy and Supabase callback params.
- `frontend/components/Dashboard.tsx`:
  - Uses auth bootstrap from URL.
  - Export requests use authenticated `apiClient`.
- `frontend/components/DetailedInsights.tsx`:
  - Export requests now use authenticated `apiClient` (no anonymous fetch path).
- `frontend/app/globals.css`:
  - Canonical Executive Indigo token layer (light/dark), chart palette, and reusable visual utilities.
- `backend/main.py`:
  - `extract_keywords()` rewritten to score meaningful phrases and suppress generic filler tokens.
  - `extract_themes()` rewritten to map reviews into canonical theme buckets with deterministic sentiment tagging.

## Implemented Milestones
1. Apify + OpenAI integrations wired and guarded for production.
2. Redis caching integrated for analyze results with reusable key format:
   - `analysis:{asin}:{country}:{max_reviews}:{enable_ai}`
3. Cache reuse flow implemented (`from_cache`, cached results listing endpoint).
4. Cloud Redis validation completed:
   - Upstash browser shows persisted `analysis:*` keys.
   - TTL behavior confirms backend cache writes are active.
5. Cache fallback hardening implemented:
   - Redis DNS/connection failures no longer disable caching completely.
   - Memory fallback preserves 48h TTL semantics while backend process is alive.
6. Auth hardening work done (email verify/reset/session infra), then migrated to Supabase-first and finally Supabase-only for protected APIs.
7. Frontend auth callback parsing expanded:
   - legacy: `verify_token`, `reset_token`
   - Supabase: `token_hash`, `type`, `access_token`, `refresh_token`
8. Export authentication fixed to use bearer-aware API client.
9. ASIN URL extraction/normalization implemented end-to-end (frontend + backend).
10. Cache UI dedupe/cooldown + clearer cache endpoint logging implemented to reduce noisy repeated cache effects.
11. Product title surfaced in analysis and cached-results UX (`product_title` added to cache results contract).
12. Strict Apify product-title mapping implemented to avoid ASIN-like/review-title product names.
13. Summary/rating correctness fixes implemented to prevent misleading `average rating 0.0` in detailed analysis.
14. Supabase recovery-link compatibility fixed for both `token_hash` and recovery-session callbacks.
15. Reset-password UI rendering fixed for recovery-session callbacks that also create a user session.
16. Backend email fallback logs no longer include body/link content.
17. Repo documentation/workflow cleanup completed with canonical docs/workflow set.
18. Legacy local-auth service/model code removed; Supabase-only runtime simplified.
19. Deployment manifest set reduced to single canonical `render.yaml`.
20. Added `frontend.md` as UI prompt source-of-truth for Pencil.dev screen generation.
21. `frontend.md` refined into a decision-complete premium redesign brief (visual-only upgrade, no IA changes).
22. Implemented `frontend.pen` visual system in the Next.js frontend while preserving existing IA/flows and protected API contracts.
23. Applied UI cleanup pass based on screenshot QA: deduped export/logout actions, moved auth/cache actions into sidebar footer, and fixed pie chart label clipping.
24. Replaced noisy keyword/theme extraction with deterministic high-signal keyword phrases and canonical theme taxonomy labels.

## API Behavior Contract (Important)
- Public:
  - `GET /`
  - `GET /health`
  - `GET /api/v1/growth/{asin}`
  - `POST /api/v1/insights`
- Protected (requires bearer token + verified user):
  - `POST /api/v1/analyze`
  - `GET /api/v1/cache/results` (entries now include `product_title`)
  - `POST /api/v1/export/csv`
  - `POST /api/v1/export/pdf`
- Deprecated (returns `410 Gone`):
  - Local auth/session routes except `/api/v1/auth/me` and `/api/v1/auth/csrf`
  - Local admin auth/session endpoints

## Env Contract (Required)
Backend required:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `APIFY_API_TOKEN`
- `ENABLE_CACHE=true`
- `REDIS_URL`
- `REDIS_TTL_SECONDS=172800`

Frontend required:
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Optional tuning:
- `SUPABASE_AUTH_TIMEOUT_SECONDS`
- `SUPABASE_AUTH_CACHE_TTL_SECONDS`
- `APIFY_TIMEOUT_SECONDS`
- `OPENAI_*` controls

## Operator Setup Pending (Manual)
- Paste real Supabase values in:
  - `backend/.env`: `SUPABASE_URL`, `SUPABASE_ANON_KEY`
  - `frontend/.env.local`: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- In Supabase dashboard, add redirect URLs:
  - `http://localhost:3000`
  - production frontend URL
- Keep Supabase Email confirmation enabled for verified-user gating.
- Use **Upstash TCP Redis** credentials (not REST URL) in `backend/.env`:
  - `REDIS_URL=rediss://default:<UPSTASH_PASSWORD>@<UPSTASH_TCP_HOST>:6379`
  - then restart backend and verify cache by running same analyze request twice (`from_cache: true` on second call).

## Dev + Verification Commands
Backend:
- `cd backend && source venv/bin/activate`
- `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- `./venv/bin/python -m pytest -q -o addopts=''`

Frontend:
- `cd frontend && npm run dev`
- `npm run type-check`
- `npm run build`

Latest known verification (April 6, 2026):
- Backend tests passed: `17 passed`.
- Frontend type-check passed.
- Frontend production build passed.
- Cache service tests (targeted) passed after fallback update: `4 passed`.
- Operator confirmed Upstash key TTL observed live (~`172512`), indicating cloud caching active.
- Additional auth/cache verification (April 6, 2026, latest patch):
  - `frontend npm run type-check` passed after recovery callback/reset UI updates.
  - `backend pytest -q -o addopts='' tests/test_supabase_auth_service.py` passed (`3 passed`).
  - `backend pytest -q -o addopts='' tests/test_cache_service.py` passed (`5 passed`).
  - Static audit confirms no active backend route sends verification/reset emails (Supabase direct flow).
- Post-cleanup verification (April 6, 2026):
  - `backend pytest -q -o addopts='' tests/test_supabase_auth_service.py tests/test_cache_service.py tests/test_apify_integration_helpers.py tests/test_openai_service_helpers.py` passed (`20 passed`).
- Frontend redesign verification (April 6, 2026, `frontend.pen` implementation):
  - `frontend npm run type-check` passed.
  - `frontend npm run build` passed.
- Frontend screenshot-fix verification (April 6, 2026):
  - `frontend npm run build` passed.
  - `frontend npm run type-check` passed.
- Keyword/theme extraction verification (April 6, 2026):
  - `backend pytest -q -o addopts='' tests/test_keyword_theme_quality.py` passed (`2 passed`).
  - `backend pytest -q -o addopts='' tests/test_supabase_auth_service.py tests/test_cache_service.py tests/test_apify_integration_helpers.py tests/test_openai_service_helpers.py tests/test_keyword_theme_quality.py` passed (`22 passed`).
  - `frontend npm run build` passed after keyword/theme UI safety-filter patch.
  - `frontend npm run type-check` passed after keyword/theme UI safety-filter patch.

## Known Historical Issues (For Faster Debugging)
- Browser CORS-looking login failure was previously caused by backend/migration/auth state, not purely CORS config.
- Email verification/reset flows are Supabase-managed; backend no longer handles or logs reset/verification link bodies.
- Supabase-only mode means old login/signup backend routes are no longer valid API clients for auth.
- Legacy local-auth service modules and related ORM token/session models have been removed from active code paths.
- If `REDIS_URL` is host-only or malformed, analysis may fail; expected valid format is `redis://` or `rediss://` with host/port and usually auth credentials.
- If Redis host cannot resolve/connect, app now falls back to memory cache and reports the root cause in `cache_last_error`.
- Apify product-not-found/empty extraction on a given ASIN currently falls back to generated mock data when `USE_MOCK_FALLBACK=true`.

## Working Rules For Future Sessions
1. Read this file + `implementation.md` first.
2. Preserve API payload compatibility for analyze/cache/export responses.
3. Do not reintroduce session-cookie auth fallback unless explicitly requested.
4. Keep default region `IN` unless product requirement changes.
5. After major code or behavior changes, append/update:
   - Current State
   - Implemented Milestones
   - API Behavior Contract
   - Latest verification results
6. Keep root docs minimal: prefer updating existing `README.md`/`AGENTS.md`/`implementation.md` instead of adding new ad-hoc markdown files.
