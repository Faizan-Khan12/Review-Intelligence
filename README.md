# Amazon Review Intelligence Dashboard

AI-powered Amazon review analysis with Redis caching, Supabase-only auth, and exportable insights.

## Overview
Amazon Review Intelligence analyzes Amazon product reviews by ASIN (or URL parsed on frontend), then returns:
- sentiment and rating distributions
- keywords/themes/emotions
- AI-generated summaries/insights (when enabled)
- export files (CSV/XLSX path and PDF)

Current active runtime:
- Backend: `backend/main.py` (`uvicorn main:app`)
- Frontend: `frontend/app/page.tsx` (`Dashboard`)

## Implemented Core Features
- Apify review fetch with mock fallback
- NLP pipeline (VADER + TextBlob + rule-based enrichment)
- Redis response caching for analyze endpoint
- Supabase bearer-token authentication for protected APIs
- Protected expensive endpoints (analyze + export)
- PostgreSQL/SQLite-ready schema with Alembic migrations
- Subscription-ready placeholder schema (Razorpay mapping fields)

## Tech Stack
### Backend
- FastAPI
- SQLAlchemy + Alembic
- Redis (optional, env-controlled)
- Supabase token validation via GoTrue `/auth/v1/user`
- pandas/numpy/nltk/textblob/vader
- Apify client

### Frontend
- Next.js 14 + TypeScript
- Axios
- Recharts + D3
- Tailwind + UI primitives

## Quick Start
### Prerequisites
- Python 3.11+ recommended
- Node 18+
- npm 9+

### 1) Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m nltk.downloader punkt stopwords vader_lexicon
cp .env.example .env
```

Run backend:
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Access:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

## Environment Variables
Use `backend/.env.example` as source of truth.

Important backend vars:
- `DATABASE_URL` (default dev: `sqlite:///./dev.db`)
- `USE_DATABASE`
- `REDIS_URL`
- `REDIS_TTL_SECONDS`
- `ENABLE_CACHE`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_AUTH_TIMEOUT_SECONDS`
- `SUPABASE_AUTH_CACHE_TTL_SECONDS`
- `APIFY_API_TOKEN`
- `ENABLE_AI`

Important frontend vars:
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## API Documentation
### Public
- `GET /`
- `GET /health`
- `GET /api/v1/growth/{asin}`
- `POST /api/v1/insights`

### Auth
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/logout-all`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/csrf`
- `POST /api/v1/auth/verify-email/request`
- `POST /api/v1/auth/verify-email/confirm`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
Note: except `/api/v1/auth/me` and `/api/v1/auth/csrf`, these endpoints are deprecated and return `410 Gone`.

### Admin
- `GET /api/v1/admin/users`
- `PATCH /api/v1/admin/users/{id}/role`
- `GET /api/v1/admin/sessions`
Note: these local-admin endpoints are deprecated and return `410 Gone`.

### Protected (verified email + auth)
- `POST /api/v1/analyze`
- `POST /api/v1/export/csv`
- `POST /api/v1/export/pdf`
- `GET /api/v1/cache/results`

Auth behavior on protected routes:
- If `Authorization: Bearer <token>` is present, backend validates Supabase token.
- If bearer token is missing/invalid/expired, backend returns `401`.

Legacy auth route behavior:
- `/api/v1/auth/me` remains available as bearer-token introspection.
- `/api/v1/auth/csrf` remains as compatibility no-op.
- Other legacy `/api/v1/auth/*` routes return `410 Gone` and should not be used.

### Analyze Request Example
```json
{
  "asin": "B08N5WRWNW",
  "country": "US",
  "max_reviews": 100,
  "enable_ai": true
}
```

## Caching Behavior
When `ENABLE_CACHE=true`, backend applies read-through Redis caching on `POST /api/v1/analyze`.

Cache key policy:
- `analysis:{asin}:{country}:{max_reviews}:{enable_ai}`

Notes:
- shared/global by request parameters (not user-scoped)
- TTL controlled by `REDIS_TTL_SECONDS` (default `172800` = 48 hours)

## Auth Behavior
- Preferred: Supabase access token in `Authorization: Bearer <jwt>`
- No cookie-session fallback is used for protected APIs.
- CSRF tokens are not required in bearer-token mode.
- Email verification and password reset are handled via Supabase Auth flows.

## Database & Migrations
- Alembic config: `backend/alembic.ini`
- Migration folder: `backend/alembic/versions/`
- Existing SQLAlchemy/Alembic schema is still present for non-auth data and historical compatibility

Run migration manually:
```bash
cd backend
./venv/bin/alembic upgrade head
```

## Notes on Exports
- `POST /api/v1/export/csv` currently uses exporter flow that writes spreadsheet-style output (historical naming kept for API compatibility).
- `POST /api/v1/export/pdf` generates a PDF report.

## Testing
Backend quick tests:
```bash
cd backend
./venv/bin/python -m pytest
```

Frontend:
```bash
cd frontend
npm run dev
```

## Deployment
Canonical deployment manifest:
- `render.yaml` (backend on Render)

For backend runtime command, use:
- `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2`

Frontend is expected to be deployed on Vercel (set `NEXT_PUBLIC_API_URL` and Supabase public env vars there).

## Roadmap
- [ ] Multi-product comparison
- [ ] Historical trend analysis
- [ ] Email report scheduling
- [x] Authentication system
- [ ] Subscription checkout + webhook integration (Razorpay)
- [ ] Admin dashboard

## License
MIT (see `LICENSE`).
