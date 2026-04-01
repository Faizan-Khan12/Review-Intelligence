# Amazon Review Intelligence Dashboard

AI-powered Amazon review analysis with caching, session auth, and exportable insights.

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
- Session-cookie authentication (signup/login/logout/me)
- Protected expensive endpoints (analyze + export)
- PostgreSQL/SQLite-ready schema with Alembic migrations
- Subscription-ready placeholder schema (Razorpay mapping fields)

## Tech Stack
### Backend
- FastAPI
- SQLAlchemy + Alembic
- Redis (optional, env-controlled)
- passlib + bcrypt (session auth)
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
- `SESSION_COOKIE_NAME`
- `SESSION_TTL_HOURS`
- `COOKIE_SECURE`
- `APIFY_API_TOKEN`
- `ENABLE_AI`

Important frontend vars:
- `NEXT_PUBLIC_API_URL`

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
- `GET /api/v1/auth/me`

### Protected (session required)
- `POST /api/v1/analyze`
- `POST /api/v1/export/csv`
- `POST /api/v1/export/pdf`
- `GET /api/v1/cache/results`

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
- TTL controlled by `REDIS_TTL_SECONDS`

## Auth Behavior
- Cookie-based session auth (`HttpOnly`, `SameSite` configurable via `COOKIE_SAMESITE`)
- `Secure` cookie forced in production
- Session records stored server-side in `user_sessions`
- For cross-domain frontend/backend deployments, set:
  - `COOKIE_SAMESITE=none`
  - `COOKIE_SECURE=true`

## Database & Migrations
- Alembic config: `backend/alembic.ini`
- Migration folder: `backend/alembic/versions/`
- Initial auth/subscription migration exists and is applied in local dev setup

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
Current repo includes multiple deployment manifests (`render.yaml`, `backend/Render.yaml`, Docker compose files, Fly config).
For backend runtime command, use:
- `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Roadmap
- [ ] Multi-product comparison
- [ ] Historical trend analysis
- [ ] Email report scheduling
- [x] Authentication system
- [ ] Subscription checkout + webhook integration (Razorpay)
- [ ] Admin dashboard

## License
MIT (see `LICENSE`).
