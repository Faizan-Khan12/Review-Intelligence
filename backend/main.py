"""
Amazon Review Intelligence - Production Backend
Real-time Apify Integration with AI/NLP Analysis
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
import asyncio
import traceback
import re
from collections import defaultdict
from io import BytesIO

# Load environment first
from dotenv import load_dotenv
load_dotenv()

# Core imports
import uvicorn
import pandas as pd
import numpy as np
from loguru import logger

# NLP imports
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import nltk

# Apify import
from apify_client import ApifyClient

# Import export service
try:
    from app.services.exporter import exporter
    EXPORTER_AVAILABLE = True
    print("✅ Exporter service loaded")
except ImportError as e:
    EXPORTER_AVAILABLE = False
    print(f"⚠️ Exporter service not available: {e}")

# Import bot detector
try:
    from app.services.bot_detector import bot_detector
    BOT_DETECTOR_AVAILABLE = True
    print("✅ Bot detector loaded")
except ImportError as e:
    BOT_DETECTOR_AVAILABLE = False
    print(f"⚠️ Bot detector not available: {e}")

# Import OpenAI service
try:
    from app.services.openai_service import openai_service
    OPENAI_AVAILABLE = openai_service.is_available()
    if OPENAI_AVAILABLE:
        print("✅ OpenAI service loaded and configured")
    else:
        print("⚠️ OpenAI service loaded but API key not configured")
except ImportError as e:
    OPENAI_AVAILABLE = False
    print(f"⚠️ OpenAI service not available: {e}")

# Import Supabase auth service
try:
    from app.services.supabase_auth_service import supabase_auth_service
    SUPABASE_AUTH_AVAILABLE = bool(getattr(supabase_auth_service, "enabled", False))
    if SUPABASE_AUTH_AVAILABLE:
        print("✅ Supabase auth service enabled")
    else:
        print("ℹ️ Supabase auth service disabled (missing env)")
except ImportError as e:
    SUPABASE_AUTH_AVAILABLE = False
    print(f"⚠️ Supabase auth service not available: {e}")

# Import cache service
try:
    from app.services.cache_service import cache_service
    CACHE_AVAILABLE = True
    print("✅ Cache service loaded")
except ImportError as e:
    CACHE_AVAILABLE = False
    print(f"⚠️ Cache service not available: {e}")

    class _NoOpCacheService:
        def get(self, key: str):
            return None

        def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
            return False

        def delete(self, key: str):
            return False

        def list_analysis_entries(self, limit: int = 20, include_payload: bool = False):
            return []

    cache_service = _NoOpCacheService()

# Initialize components
vader_analyzer = SentimentIntensityAnalyzer()

# Simple configuration
class Config:
    # App settings
    APP_NAME = os.getenv("APP_NAME", "Amazon Review Intelligence")
    APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # CORS
    ALLOWED_ORIGINS = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    
    # Apify
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
    APIFY_ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "junglee/amazon-reviews-scraper")
    APIFY_TIMEOUT_SECONDS = int(os.getenv("APIFY_TIMEOUT_SECONDS", "180"))
    
    # Features
    ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
    MAX_REVIEWS = int(os.getenv("MAX_REVIEWS_PER_REQUEST", "100"))
    USE_MOCK_FALLBACK = os.getenv("USE_MOCK_FALLBACK", "true").lower() == "true"

    # Auth/session
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "ari_session")
    SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "720"))
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE = os.getenv(
        "COOKIE_SAMESITE",
        "none" if ENVIRONMENT == "production" else "lax",
    ).lower()
    CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "ari_csrf")
    CSRF_HEADER_NAME = os.getenv("CSRF_HEADER_NAME", "X-CSRF-Token")
    EMAIL_VERIFY_TOKEN_TTL_MINUTES = int(os.getenv("EMAIL_VERIFY_TOKEN_TTL_MINUTES", "1440"))
    PASSWORD_RESET_TOKEN_TTL_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_TTL_MINUTES", "30"))
    FRONTEND_APP_URL = os.getenv("FRONTEND_APP_URL", "http://localhost:3000")

    AUTH_RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("AUTH_RATE_LIMIT_LOGIN_PER_MINUTE", "10"))
    AUTH_RATE_LIMIT_SIGNUP_PER_HOUR = int(os.getenv("AUTH_RATE_LIMIT_SIGNUP_PER_HOUR", "10"))
    AUTH_RATE_LIMIT_PASSWORD_RESET_PER_HOUR = int(os.getenv("AUTH_RATE_LIMIT_PASSWORD_RESET_PER_HOUR", "5"))

config = Config()

# Initialize Apify client
apify_client = None
if config.APIFY_API_TOKEN:
    try:
        apify_client = ApifyClient(config.APIFY_API_TOKEN)
        logger.info("✅ Apify client initialized")
    except Exception as e:
        logger.error(f"❌ Apify initialization failed: {e}")

# Growth data storage (in-memory for now)
growth_data_store = defaultdict(list)

# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 60)
    logger.info(f"🚀 {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"📊 Apify Token: {'✅ Configured' if config.APIFY_API_TOKEN else '❌ Not configured'}")
    logger.info(f"🤖 AI Analysis: {'Enabled' if config.ENABLE_AI else 'Disabled'}")
    logger.info(f"🌐 CORS Origins: {config.ALLOWED_ORIGINS}")
    logger.info("=" * 60)
    
    # Download NLTK data
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('vader_lexicon', quiet=True)
        logger.info("✅ NLTK data ready")
    except Exception as e:
        logger.warning(f"⚠️ NLTK setup: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down...")

# Create FastAPI app
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Apply basic security headers for browser clients."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if config.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# ============= HELPER FUNCTIONS =============

def analyze_sentiment(text: str) -> Dict:
    """Analyze sentiment using VADER and TextBlob"""
    # VADER analysis
    vader_scores = vader_analyzer.polarity_scores(text)
    
    # TextBlob analysis
    blob = TextBlob(text)
    
    # Determine overall sentiment
    compound = vader_scores['compound']
    if compound >= 0.05:
        sentiment = "positive"
    elif compound <= -0.05:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    return {
        "sentiment": sentiment,
        "confidence": abs(compound),
        "scores": {
            "positive": vader_scores['pos'],
            "neutral": vader_scores['neu'],
            "negative": vader_scores['neg'],
            "compound": compound
        },
        "polarity": blob.sentiment.polarity,
        "subjectivity": blob.sentiment.subjectivity
    }


ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")
ASIN_URL_PATTERNS = [
    re.compile(r"/dp/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE),
    re.compile(r"/gp/product/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE),
    re.compile(r"/product/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE),
    re.compile(r"/ASIN/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE),
]


def normalize_asin(value: Any) -> Optional[str]:
    """Normalize ASIN from plain value or Amazon product URL."""
    raw = str(value or "").strip()
    if not raw:
        return None

    candidate = raw.upper()
    if ASIN_PATTERN.fullmatch(candidate):
        return candidate

    for pattern in ASIN_URL_PATTERNS:
        match = pattern.search(raw)
        if match and match.group(1):
            extracted = match.group(1).upper()
            if ASIN_PATTERN.fullmatch(extracted):
                return extracted

    return None


def build_analysis_cache_key(asin: str, country: str, max_reviews: int, enable_ai: bool) -> str:
    """Build cache key for analysis endpoint response."""
    return f"analysis:{asin}:{country}:{max_reviews}:{int(bool(enable_ai))}"


@dataclass
class AuthPrincipal:
    """Normalized authenticated principal (local session or Supabase token)."""

    id: str
    email: str
    role: str = "user"
    is_active: bool = True
    email_verified_at: Optional[datetime] = None
    provider: str = "local"
    raw: Optional[Dict[str, Any]] = None


def _user_payload(user) -> Dict[str, Any]:
    """Serialize user for API responses."""
    user_id = getattr(user, "id", "")
    if isinstance(user_id, (int, float)):
        payload_id: Any = int(user_id)
    else:
        payload_id = str(user_id)
    return {
        "id": payload_id,
        "email": getattr(user, "email", ""),
        "role": getattr(user, "role", "user"),
        "is_active": bool(getattr(user, "is_active", True)),
        "email_verified": bool(getattr(user, "email_verified_at", None)),
        "email_verified_at": (
            getattr(user, "email_verified_at").isoformat()
            if getattr(user, "email_verified_at", None)
            else None
        ),
    }


def _ensure_auth_available() -> None:
    if not SUPABASE_AUTH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Supabase auth is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.",
        )


def _extract_bearer_token(request: Request) -> str:
    """Extract bearer token from Authorization header."""
    header = request.headers.get("authorization", "")
    if not header:
        return ""
    prefix = "bearer "
    if header.lower().startswith(prefix):
        return header[len(prefix):].strip()
    return ""


def _principal_from_supabase(request: Request) -> Optional[AuthPrincipal]:
    """Resolve principal from Supabase bearer token when configured."""
    if not SUPABASE_AUTH_AVAILABLE:
        return None

    token = _extract_bearer_token(request)
    if not token:
        return None

    principal_data = supabase_auth_service.get_principal_from_token(token)
    if not principal_data:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    return AuthPrincipal(
        id=str(principal_data.get("id", "")),
        email=str(principal_data.get("email", "")),
        role=str(principal_data.get("role", "user")),
        is_active=bool(principal_data.get("is_active", True)),
        email_verified_at=principal_data.get("email_verified_at"),
        provider="supabase",
        raw=principal_data.get("raw"),
    )


def get_optional_current_user(request: Request):
    """Resolve current user from Supabase token when present."""
    return _principal_from_supabase(request)


def get_current_user(request: Request):
    """Resolve current authenticated user from Supabase bearer token."""
    _ensure_auth_available()

    supabase_principal = _principal_from_supabase(request)
    if supabase_principal:
        return supabase_principal

    raise HTTPException(status_code=401, detail="Missing bearer token")


def require_verified_user(current_user=Depends(get_current_user)):
    if not current_user.email_verified_at:
        raise HTTPException(status_code=403, detail="Email verification required")
    return current_user


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_csrf(request: Request):
    """No-op in Supabase bearer-token mode."""
    return


def _reject_legacy_auth_route(route_name: str) -> None:
    """Reject deprecated local-auth routes after Supabase migration."""
    raise HTTPException(
        status_code=410,
        detail=(
            f"'{route_name}' is deprecated. Use Supabase Auth from the frontend client "
            "and pass Authorization: Bearer <token> to backend protected APIs."
        ),
    )

LOW_VALUE_KEYWORDS = {
    "good", "great", "okay", "ok", "nice", "bad", "best", "better", "worse",
    "average", "perfect", "excellent", "amazing", "awesome", "fine", "decent",
    "product", "item", "thing", "stuff", "works", "work", "working", "use",
    "used", "using", "value", "money", "fast", "slow", "time", "day",
    "buy", "bought", "purchase", "review", "reviews",
}

KEYWORD_SIGNAL_WORDS = {
    "battery", "quality", "sound", "noise", "cancellation", "comfort", "fit",
    "delivery", "shipping", "packaging", "durability", "price", "performance",
    "connectivity", "bluetooth", "app", "setup", "microphone", "charging",
}

THEME_RULES: Dict[str, List[str]] = {
    "Sound Quality": ["sound quality", "sound", "audio", "bass", "treble", "volume", "voice clarity"],
    "Noise Cancellation": ["noise cancellation", "anc", "noise canceling", "background noise"],
    "Battery Life": ["battery life", "battery", "charging", "charge", "power backup"],
    "Build Quality": ["build quality", "material", "sturdy", "durable", "construction", "premium feel"],
    "Comfort & Fit": ["comfort", "comfortable", "fit", "ear tips", "lightweight", "wearing"],
    "Connectivity": ["connectivity", "bluetooth", "connection", "pairing", "disconnect", "app"],
    "Delivery & Packaging": ["delivery", "shipping", "arrived", "packaging", "package", "box"],
    "Value for Money": ["price", "cost", "worth", "value for money", "expensive", "cheap"],
    "Ease of Use": ["easy to use", "easy setup", "setup", "simple", "user friendly", "intuitive"],
    "Durability & Reliability": ["durable", "reliable", "lasted", "broke", "stopped working", "defective"],
}


def _get_english_stopwords() -> set:
    try:
        from nltk.corpus import stopwords

        return set(stopwords.words("english"))
    except Exception:
        return {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
            "with", "by", "from", "up", "about", "into", "through", "during", "before",
            "after", "above", "below", "between", "under", "again", "further", "then",
            "once", "this", "that", "these", "those", "very", "really",
        }


def _normalize_token(token: str) -> str:
    token = token.strip().lower()
    if len(token) <= 2 or not token.isalpha():
        return ""
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
        return token[:-1]
    return token


def extract_keywords(texts: List[str], top_n: int = 10) -> List[Dict]:
    """
    Extract high-signal keywords/phrases from review text.
    Uses document frequency + phrase bias and removes low-value generic words.
    """
    from collections import Counter

    if not texts:
        return []

    stop_words = _get_english_stopwords()
    generic_terms = stop_words | LOW_VALUE_KEYWORDS
    doc_frequency: Counter = Counter()
    total_frequency: Counter = Counter()
    min_doc_freq = 2 if len(texts) >= 3 else 1

    for text in texts:
        raw_tokens = re.findall(r"[a-zA-Z]+", str(text).lower())
        tokens = [_normalize_token(tok) for tok in raw_tokens]
        tokens = [tok for tok in tokens if tok and tok not in stop_words]
        if not tokens:
            continue

        candidates: List[str] = []

        # Strong unigrams only
        for tok in tokens:
            if tok in generic_terms:
                continue
            candidates.append(tok)

        # Bigrams provide better semantic value than isolated adjectives.
        for idx in range(len(tokens) - 1):
            chunk = tokens[idx : idx + 2]
            if any(word in stop_words for word in chunk):
                continue
            if all(word in generic_terms for word in chunk):
                continue
            if chunk[-1] in {"product", "item", "thing"}:
                continue
            candidates.append(" ".join(chunk))

        for candidate in candidates:
            total_frequency[candidate] += 1
        for candidate in set(candidates):
            doc_frequency[candidate] += 1

    scored: List[tuple[str, float]] = []
    for term, doc_count in doc_frequency.items():
        if doc_count < min_doc_freq:
            continue

        words = term.split()
        if len(words) == 1 and term in generic_terms:
            continue

        phrase_bonus = 2.0 if len(words) == 2 else (3.0 if len(words) >= 3 else 0.0)
        signal_bonus = 1.5 if any(word in KEYWORD_SIGNAL_WORDS for word in words) else 0.0
        score = (doc_count * 3.0) + total_frequency[term] + phrase_bonus + signal_bonus
        scored.append((term, score))

    scored.sort(key=lambda item: (-item[1], -doc_frequency[item[0]], -len(item[0].split()), item[0]))

    selected: List[str] = []
    for term, _score in scored:
        # Avoid noisy duplication: if unigram already covered by a selected phrase, skip it.
        if len(term.split()) == 1:
            if any(term in phrase.split() for phrase in selected if len(phrase.split()) > 1):
                continue
        selected.append(term)
        if len(selected) >= top_n:
            break

    return [{"word": term, "frequency": int(doc_frequency[term])} for term in selected]

def generate_mock_reviews(asin: str, count: int = 50) -> Dict:
    """Generate mock reviews as fallback"""
    import random
    
    reviews = []
    for i in range(count):
        rating = random.choice([5, 5, 4, 4, 4, 3, 3, 2, 1])
        
        positive_texts = [
            "Great product, highly recommend!",
            "Excellent quality and fast shipping.",
            "Exactly as described, very satisfied.",
            "Amazing value for money!",
            "Perfect, couldn't be happier!"
        ]
        
        negative_texts = [
            "Poor quality, disappointed.",
            "Not as described, returning.",
            "Broke after one week.",
            "Waste of money.",
            "Terrible experience."
        ]
        
        neutral_texts = [
            "It's okay, nothing special.",
            "Average product.",
            "Does the job.",
            "Acceptable quality.",
            "Fine for the price."
        ]
        
        if rating >= 4:
            text = random.choice(positive_texts)
        elif rating <= 2:
            text = random.choice(negative_texts)
        else:
            text = random.choice(neutral_texts)
        
        reviews.append({
            "id": f"mock_{i}",
            "rating": rating,
            "title": text.split(',')[0],
            "text": text,
            "author": f"Customer_{i}",
            "date": datetime.now().isoformat(),
            "verified": random.choice([True, False]),
            "helpful_count": random.randint(0, 100)
        })
    
    # Calculate statistics
    ratings = [r['rating'] for r in reviews]
    
    return {
        "success": True,
        "asin": asin,
        "reviews": reviews,
        "total_reviews": len(reviews),
        "average_rating": sum(ratings) / len(ratings) if ratings else 0,
        "rating_distribution": {
            "5": len([r for r in ratings if r == 5]),
            "4": len([r for r in ratings if r == 4]),
            "3": len([r for r in ratings if r == 3]),
            "2": len([r for r in ratings if r == 2]),
            "1": len([r for r in ratings if r == 1])
        },
        "product_info": {
            "title": f"Product {asin}",
            "brand": "Generic Brand",
            "price": "$99.99",
            "image": "https://via.placeholder.com/200"
        },
        "data_source": "mock"
    }


def _coerce_int(value: Any, default: int = 0) -> int:
    """Safely coerce heterogeneous values into int."""
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return default
    try:
        return int(float(match.group(0)))
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any, default: bool = False) -> bool:
    """Safely coerce values into bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "verified"}
    return default


def _parse_rating(value: Any, default: float = 0.0) -> float:
    """Extract a numeric rating from formats like '4.0 out of 5 stars'."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return default
    try:
        return float(match.group(0))
    except (TypeError, ValueError):
        return default


def _read_apify_dataset_items(dataset_client, limit: int) -> List[Dict[str, Any]]:
    """Collect a bounded number of dataset rows to avoid unbounded memory usage."""
    items: List[Dict[str, Any]] = []
    for item in dataset_client.iterate_items():
        if isinstance(item, dict):
            items.append(item)
        if len(items) >= limit:
            break
    return items


def _extract_product_title_from_item(item: Dict[str, Any]) -> str:
    """Extract product title only from product-level fields (never review title keys)."""
    for key in ("productTitle", "productName"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    # `name` is only trusted when the row has clear product-level metadata.
    product_context = any(
        item.get(field) is not None
        for field in (
            "asin",
            "brand",
            "manufacturer",
            "price",
            "thumbnailImage",
            "image",
            "imageUrl",
            "averageRating",
            "totalReviews",
            "reviewsCount",
        )
    )
    if product_context:
        value = item.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _extract_product_info(dataset_items: List[Dict[str, Any]], asin: str) -> Dict[str, Any]:
    """Extract product-level metadata from any row that contains it."""
    for item in dataset_items:
        title = _extract_product_title_from_item(item)
        brand = item.get("brand") or item.get("manufacturer")
        price = item.get("price")
        image = item.get("thumbnailImage") or item.get("image") or item.get("imageUrl")
        avg_rating = item.get("averageRating") or item.get("rating")
        total_reviews = item.get("totalReviews") or item.get("reviewsCount")
        item_asin = item.get("asin") or asin

        if any([title, brand, price, image, avg_rating, total_reviews]):
            return {
                "title": title or f"Product {asin}",
                "brand": brand or "",
                "price": price or "",
                "image": image or "",
                "rating": _parse_rating(avg_rating, 0.0),
                "total_reviews": _coerce_int(total_reviews, 0),
                "asin": str(item_asin or asin),
            }

    logger.debug(f"Apify product title missing for ASIN {asin}; using ASIN-based fallback title")
    return {
        "title": f"Product {asin}",
        "brand": "",
        "price": "",
        "image": "",
        "rating": 0.0,
        "total_reviews": 0,
        "asin": asin,
    }


def _iter_apify_review_rows(dataset_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Flatten dataset rows into review-like rows.
    Handles both:
    - flat rows where each row is one review
    - rows containing nested `reviews` arrays
    """
    rows: List[Dict[str, Any]] = []
    for item in dataset_items:
        nested_reviews = item.get("reviews")
        if isinstance(nested_reviews, list) and nested_reviews:
            for nested in nested_reviews:
                if isinstance(nested, dict):
                    merged = dict(item)
                    merged.update(nested)
                    rows.append(merged)
            continue
        rows.append(item)
    return rows


def _normalize_apify_review(item: Dict[str, Any], idx: int) -> Optional[Dict[str, Any]]:
    """Normalize different Apify review schemas into one internal shape."""
    title = (
        item.get("reviewTitle")
        or item.get("title")
        or item.get("headline")
        or ""
    )
    text = (
        item.get("reviewDescription")
        or item.get("reviewText")
        or item.get("text")
        or item.get("content")
        or ""
    )
    if not title and not text:
        return None

    raw_rating = (
        item.get("reviewRating")
        or item.get("rating")
        or item.get("stars")
        or item.get("score")
        or item.get("ratingScore")
        or item.get("ratingValue")
        or item.get("starRating")
        or item.get("reviewStars")
        or item.get("reviewScore")
    )
    if isinstance(raw_rating, dict):
        raw_rating = (
            raw_rating.get("rating")
            or raw_rating.get("score")
            or raw_rating.get("value")
            or raw_rating.get("overall")
        )

    rating = _parse_rating(raw_rating, 0.0)

    return {
        "id": str(item.get("id") or item.get("reviewId") or f"apify_{idx}"),
        "title": str(title),
        "text": str(text),
        "rating": rating,
        "author": str(
            item.get("reviewAuthor")
            or item.get("authorName")
            or item.get("author")
            or "Anonymous"
        ),
        "date": str(item.get("reviewDate") or item.get("date") or item.get("reviewedAt") or ""),
        "verified": _coerce_bool(
            item.get("isVerified")
            if item.get("isVerified") is not None
            else item.get("verifiedPurchase", item.get("verified"))
        ),
        "helpful_count": _coerce_int(
            item.get("helpfulCount")
            if item.get("helpfulCount") is not None
            else item.get("helpfulVotes", item.get("helpful"))
        ),
    }


async def fetch_apify_reviews(asin: str, max_reviews: int = 50, country: str = "IN") -> Dict:
    """Fetch real reviews from Apify"""
    if not apify_client:
        logger.warning("Apify client not initialized")
        if config.USE_MOCK_FALLBACK:
            logger.info("Using mock fallback data")
            return generate_mock_reviews(asin, max_reviews)
        return {"success": False, "error": "Apify client is not configured"}
    
    try:
        logger.info(f"📡 Fetching reviews from Apify for ASIN: {asin}")
        
        # Prepare Amazon URL
        country_domains = {
            "US": "amazon.com",
            "UK": "amazon.co.uk",
            "DE": "amazon.de",
            "FR": "amazon.fr",
            "IT": "amazon.it",
            "ES": "amazon.es",
            "CA": "amazon.ca",
            "IN": "amazon.in",
            "JP": "amazon.co.jp"
        }
        
        domain = country_domains.get(country, "amazon.com")
        amazon_url = f"https://www.{domain}/dp/{asin}"
        
        # Prepare actor input
        actor_input = {
            "productUrls": [{"url": amazon_url}],
            "maxReviews": max_reviews,
            "sort": "recent",
            "reviewsSort": "recent",
            "filterByRatings": ["allStars"],
            "scrapeProductDetails": True
        }
        
        # Run the actor
        logger.info(f"🚀 Starting Apify actor: {config.APIFY_ACTOR_ID}")
        wait_secs = max(30, min(config.APIFY_TIMEOUT_SECONDS, 600))
        run = await asyncio.to_thread(
            apify_client.actor(config.APIFY_ACTOR_ID).call,
            run_input=actor_input,
            wait_secs=wait_secs,
        )
        
        # Get results
        dataset_items = []
        if run.get("defaultDatasetId"):
            dataset_client = apify_client.dataset(run["defaultDatasetId"])
            item_limit = max(200, max_reviews * 5)
            dataset_items = await asyncio.to_thread(
                _read_apify_dataset_items,
                dataset_client,
                item_limit,
            )
        
        if not dataset_items:
            logger.warning("No data returned from Apify")
            if config.USE_MOCK_FALLBACK:
                return generate_mock_reviews(asin, max_reviews)
            return {"success": False, "error": "No data from Apify"}
        
        # Process results
        product_info = _extract_product_info(dataset_items, asin)
        review_rows = _iter_apify_review_rows(dataset_items)
        all_reviews: List[Dict[str, Any]] = []

        for idx, item in enumerate(review_rows):
            normalized = _normalize_apify_review(item, idx)
            if not normalized:
                continue
            all_reviews.append(normalized)
            if len(all_reviews) >= max_reviews:
                break
        
        if not all_reviews:
            logger.warning("No reviews extracted from Apify data")
            if config.USE_MOCK_FALLBACK:
                return generate_mock_reviews(asin, max_reviews)
            return {
                "success": False,
                "error": "Apify run completed but no review rows were extracted. "
                         "Verify APIFY_ACTOR_ID and actor input schema.",
            }
        
        # Calculate statistics
        ratings = [float(r.get("rating", 0) or 0) for r in all_reviews]
        valid_ratings = [value for value in ratings if value > 0]
        rating_distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
        for rating in valid_ratings:
            bucket = str(max(1, min(5, int(round(rating)))))
            rating_distribution[bucket] += 1
        average_rating = (
            sum(valid_ratings) / len(valid_ratings)
            if valid_ratings
            else _parse_rating(product_info.get("rating"), 0.0)
        )
        
        logger.info(f"✅ Successfully fetched {len(all_reviews)} reviews from Apify")
        
        return {
            "success": True,
            "asin": asin,
            "reviews": all_reviews,
            "total_reviews": len(all_reviews),
            "average_rating": average_rating,
            "rating_distribution": rating_distribution,
            "product_info": product_info,
            "data_source": "apify"
        }
        
    except Exception as e:
        logger.error(f"Apify error: {e}\n{traceback.format_exc()}")
        if config.USE_MOCK_FALLBACK:
            logger.info("Falling back to mock data")
            return generate_mock_reviews(asin, max_reviews)
        return {"success": False, "error": str(e)}

def extract_emotions(texts: List[str]) -> Dict[str, float]:
    """Extract 8-dimension emotion scores (Plutchik's model)"""
    from textblob import TextBlob
    
    # Emotion keywords (simplified emotion detection)
    emotion_keywords = {
        "joy": ["happy", "joy", "love", "excellent", "amazing", "wonderful", "great", "perfect", "delighted"],
        "sadness": ["sad", "disappointed", "unhappy", "regret", "poor", "terrible", "awful", "bad"],
        "anger": ["angry", "annoyed", "frustrated", "furious", "hate", "worst", "horrible", "disgusting"],
        "fear": ["afraid", "worried", "concerned", "anxious", "scared", "nervous", "hesitant"],
        "surprise": ["surprised", "unexpected", "shocked", "amazed", "astonished", "wow"],
        "disgust": ["disgusting", "gross", "revolting", "repulsive", "nasty", "horrible"],
        "trust": ["trust", "reliable", "confident", "recommended", "authentic", "genuine", "verified"],
        "anticipation": ["excited", "looking forward", "can't wait", "anticipate", "expect", "hope"]
    }
    
    emotion_scores = {emotion: 0.0 for emotion in emotion_keywords.keys()}
    
    if not texts:
        return emotion_scores
    
    total_matches = 0
    for text in texts:
        text_lower = text.lower()
        for emotion, keywords in emotion_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            emotion_scores[emotion] += matches
            total_matches += matches
    
    # Normalize scores to 0-1 range
    if total_matches > 0:
        for emotion in emotion_scores:
            emotion_scores[emotion] = min(1.0, emotion_scores[emotion] / (len(texts) * 2))
    
    # Apply sentiment bias for more realistic scores
    avg_sentiment = sum(TextBlob(t).sentiment.polarity for t in texts) / len(texts) if texts else 0
    if avg_sentiment > 0:
        emotion_scores["joy"] = min(1.0, emotion_scores["joy"] + 0.2)
        emotion_scores["trust"] = min(1.0, emotion_scores["trust"] + 0.15)
    elif avg_sentiment < 0:
        emotion_scores["sadness"] = min(1.0, emotion_scores["sadness"] + 0.15)
        emotion_scores["anger"] = min(1.0, emotion_scores["anger"] + 0.1)
    
    return emotion_scores

def extract_themes(texts: List[str], sentiment_counts: dict) -> List[Dict[str, Any]]:
    """
    Extract stable, interpretable themes from review texts.
    Replaces unstable cluster-label naming with canonical theme buckets.
    """
    from collections import Counter, defaultdict

    if not texts:
        return []

    theme_mentions: Counter = Counter()
    theme_sentiments = defaultdict(Counter)

    for text in texts:
        text_value = str(text or "")
        if not text_value:
            continue
        lower_text = text_value.lower()

        compound = vader_analyzer.polarity_scores(text_value).get("compound", 0.0)
        review_sentiment = "neutral"
        if compound >= 0.2:
            review_sentiment = "positive"
        elif compound <= -0.2:
            review_sentiment = "negative"

        for theme_name, markers in THEME_RULES.items():
            if any(re.search(rf"\b{re.escape(marker)}\b", lower_text) for marker in markers):
                theme_mentions[theme_name] += 1
                theme_sentiments[theme_name][review_sentiment] += 1

    if not theme_mentions:
        return simple_theme_extraction(texts)

    resolved_themes: List[Dict[str, Any]] = []
    for theme_name, mentions in theme_mentions.items():
        votes = theme_sentiments.get(theme_name, {})
        sentiment = max(("positive", "neutral", "negative"), key=lambda key: votes.get(key, 0))
        resolved_themes.append(
            {
                "theme": theme_name,
                "mentions": int(mentions),
                "sentiment": sentiment,
            }
        )

    # Keep deterministic business-priority order from THEME_RULES for ties.
    resolved_themes.sort(key=lambda item: -item["mentions"])
    return resolved_themes[:5]


def simple_theme_extraction(texts: List[str]) -> List[Dict[str, Any]]:
    """
    Fallback theme extraction derived from high-signal keywords.
    """
    keyword_candidates = extract_keywords(texts, top_n=8)
    if not keyword_candidates:
        return []

    positive_markers = {"excellent", "great", "love", "satisfied", "perfect", "reliable"}
    negative_markers = {"poor", "bad", "terrible", "disappointed", "broken", "defective"}

    themes: List[Dict[str, Any]] = []
    for candidate in keyword_candidates[:5]:
        phrase = str(candidate.get("word", "")).strip()
        if not phrase:
            continue
        lower_phrase = phrase.lower()

        sentiment = "neutral"
        if any(marker in lower_phrase for marker in positive_markers):
            sentiment = "positive"
        elif any(marker in lower_phrase for marker in negative_markers):
            sentiment = "negative"

        themes.append(
            {
                "theme": phrase.title(),
                "mentions": int(candidate.get("frequency", 0)),
                "sentiment": sentiment,
            }
        )

    return themes[:5]


def generate_summaries(reviews: List[Dict], sentiment_counts: Dict[str, int], 
                       keywords: List[Dict], themes: List[Dict]) -> Dict[str, str]:
    """Generate comprehensive summaries"""
    total = len(reviews)
    if total == 0:
        return {
            "overall": "No reviews available for analysis.",
            "positive_highlights": "N/A",
            "negative_highlights": "N/A"
        }
    
    positive_count = sentiment_counts.get('positive', 0)
    negative_count = sentiment_counts.get('negative', 0)
    neutral_count = sentiment_counts.get('neutral', 0)
    
    # Overall Summary
    sentiment_desc = "positive" if positive_count > negative_count else ("negative" if negative_count > positive_count else "mixed")
    top_keywords_str = ", ".join([k["word"] for k in keywords[:5]]) if keywords else "N/A"
    
    overall = (
        f"Analyzed {total} customer reviews with an overall {sentiment_desc} sentiment. "
        f"{positive_count} reviews were positive ({positive_count/total*100:.1f}%), "
        f"{negative_count} were negative ({negative_count/total*100:.1f}%), "
        f"and {neutral_count} were neutral ({neutral_count/total*100:.1f}%). "
        f"The most frequently mentioned topics include: {top_keywords_str}."
    )
    
    # Positive Highlights
    positive_reviews = [r for r in reviews if r.get("sentiment") == "positive"]
    if positive_reviews and keywords:
        positive_keywords = [k["word"] for k in keywords[:3]]
        positive_highlights = (
            f"Customers particularly appreciate the {', '.join(positive_keywords)}. "
            f"Many reviewers highlight the product's strengths in these areas, "
            f"with {len(positive_reviews)} customers expressing high satisfaction."
        )
    else:
        positive_highlights = "Limited positive feedback available."
    
    # Negative Highlights
    negative_reviews = [r for r in reviews if r.get("sentiment") == "negative"]
    if negative_reviews:
        negative_themes = [t["theme"] for t in themes if t.get("sentiment") == "negative"][:3]
        if negative_themes:
            negative_highlights = (
                f"Some customers raised concerns about {', '.join(negative_themes).lower()}. "
                f"{len(negative_reviews)} reviews mentioned issues that may require attention, "
                f"particularly regarding quality and performance expectations."
            )
        else:
            negative_highlights = f"{len(negative_reviews)} customers expressed dissatisfaction with various aspects of the product."
    else:
        negative_highlights = "No significant negative feedback found."
    
    return {
        "overall": overall,
        "positive_highlights": positive_highlights,
        "negative_highlights": negative_highlights
    }

def analyze_reviews(reviews: List[Dict], filter_bots: bool = True) -> Dict:
    """Analyze reviews with AI/NLP and bot detection"""
    if not reviews:
        return {}

    # Step 1: Bot detection
    bot_analysis = None
    if BOT_DETECTOR_AVAILABLE and filter_bots:
        print(f"  🤖 Running bot detection on {len(reviews)} reviews...")
        bot_analysis = bot_detector.analyze_batch(reviews)
        genuine_reviews = bot_analysis.get('genuine_reviews', reviews)
        bot_stats = bot_analysis.get('bot_statistics', {})

        print(f"  ✅ Bot detection complete:")
        print(f"     - Genuine: {bot_stats.get('genuine_count', 0)}")
        print(f"     - Bots: {bot_stats.get('bot_count', 0)} ({bot_stats.get('bot_percentage', 0)}%)")

        reviews_to_analyze = genuine_reviews
    else:
        reviews_to_analyze = reviews
        bot_stats = {"total_reviews": len(reviews), "genuine_count": len(reviews), "bot_count": 0}

    # Step 2: Sentiment analysis
    analyzed = []
    sentiments = []
    texts = []

    for review in reviews_to_analyze:
        text = f"{review.get('title', '')} {review.get('text', '')}"
        texts.append(text)

        # Sentiment analysis
        sentiment_result = analyze_sentiment(text)
        sentiments.append(sentiment_result['sentiment'])

        # Add analysis to review
        analyzed.append({
            **review,
            "sentiment": sentiment_result['sentiment'],
            "sentiment_score": sentiment_result.get('polarity', 0),
            "sentiment_analysis": {
                "sentiment": sentiment_result['sentiment'],
                "vader_compound": sentiment_result.get('vader_compound', 0),
                "textblob_polarity": sentiment_result.get('polarity', 0),
                "confidence": sentiment_result.get('confidence', 0),
                "subjectivity": sentiment_result.get('subjectivity', 0)
            }
        })

    # Step 3: Aggregate metrics
    sentiment_counts = pd.Series(sentiments).value_counts().to_dict()

    # Step 4: Extract keywords (with 'frequency' field)
    keywords_raw = extract_keywords(texts, top_n=15)
    keywords = [{"word": k["word"], "frequency": k.get("count", k.get("frequency", 0))} for k in keywords_raw]

    # ✅ Step 5: EMOTION ANALYSIS (8-dimension)
    emotions = extract_emotions(texts)

    # ✅ Step 6: THEME CLUSTERING
    themes = extract_themes(texts, sentiment_counts)

    # ✅ Step 7: REVIEW SAMPLES
    review_samples = {
        "positive": [r for r in analyzed if r.get("sentiment") == "positive"][:3],
        "negative": [r for r in analyzed if r.get("sentiment") == "negative"][:3],
        "neutral": [r for r in analyzed if r.get("sentiment") == "neutral"][:3]
    }

    # Step 8: Generate insights and summary
    total = len(reviews_to_analyze)
    positive_pct = (sentiment_counts.get('positive', 0) / total * 100) if total else 0
    negative_pct = (sentiment_counts.get('negative', 0) / total * 100) if total else 0

    # Use OpenAI for better insights if available
    if OPENAI_AVAILABLE:
        try:
            print("  🤖 Generating AI-powered insights with OpenAI...")
            insights = openai_service.generate_insights(
                reviews_to_analyze,
                sentiment_counts,
                keywords
            )
            print(f"  ✅ OpenAI insights generated")
        except Exception as e:
            print(f"  ⚠️ OpenAI insights failed, using fallback: {e}")
            insights = []
    else:
        insights = []

    # Fallback insights if OpenAI unavailable or failed
    if not insights:
        if positive_pct > 70:
            insights.append(f"⭐ Excellent satisfaction: {positive_pct:.1f}% positive reviews")
        elif positive_pct > 50:
            insights.append(f"✅ Good satisfaction: {positive_pct:.1f}% positive reviews")

        if negative_pct > 30:
            insights.append(f"⚠️ High negativity: {negative_pct:.1f}% negative reviews")

        if keywords:
            top_words = ", ".join([k['word'] for k in keywords[:5]])
            insights.append(f"🔤 Top keywords: {top_words}")

    # Add bot detection insight
    if BOT_DETECTOR_AVAILABLE and filter_bots and bot_stats.get('bot_count', 0) > 0:
        insights.append(f"🤖 Filtered {bot_stats['bot_count']} bot/fake reviews ({bot_stats.get('bot_percentage', 0)}%)")

    # ✅ Step 9: COMPREHENSIVE SUMMARIES
    summaries = generate_summaries(analyzed, sentiment_counts, keywords, themes)

    return {
        "reviews": analyzed,
        "sentiment_distribution": {
            "positive": sentiment_counts.get('positive', 0),
            "neutral": sentiment_counts.get('neutral', 0),
            "negative": sentiment_counts.get('negative', 0)
        },
        "top_keywords": keywords,
        "themes": themes,
        "emotions": emotions,
        "summaries": summaries,
        "review_samples": review_samples,
        "insights": insights,
        "bot_detection": bot_stats if BOT_DETECTOR_AVAILABLE else None,
        "ai_provider": "openai" if OPENAI_AVAILABLE else "free"
    }


def generate_growth_data(asin: str, period: str = "week") -> List[Dict]:
    """Generate buyer growth data"""
    import random
    from datetime import datetime, timedelta
    
    data = []
    base_buyers = random.randint(100, 500)
    
    if period == "day":
        hours = 24
        for i in range(hours):
            time = datetime.now() - timedelta(hours=hours-i)
            buyers = base_buyers + random.randint(-20, 50)
            data.append({
                "date": time.strftime("%H:%M"),
                "buyers": buyers,
                "trend": "up" if random.random() > 0.5 else "down"
            })
    else:  # week
        days = 7
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i-1)
            buyers = base_buyers + (i * random.randint(5, 20)) + random.randint(-30, 30)
            data.append({
                "date": date.strftime("%a"),
                "buyers": max(50, buyers),
                "trend": "up" if i > days/2 else "down"
            })
    
    return data

# ============= API ENDPOINTS =============
@app.get("/api/v1/growth/{asin}")
async def get_buyer_growth(asin: str, period: str = "week"):
    """
    Generate buyer growth data for visualization
    This is MOCK DATA for demonstration - integrate with real data source later
    """
    try:
        from datetime import datetime, timedelta
        import random
        
        # Generate mock growth data based on period
        periods = {
            "day": 7,
            "week": 12,
            "month": 6,
            "quarter": 4
        }
        
        data_points = periods.get(period, 12)
        now = datetime.now()
        
        growth_data = []
        base_buyers = 1000
        
        for i in range(data_points):
            if period == "day":
                date = (now - timedelta(days=data_points - i - 1)).strftime("%Y-%m-%d")
                label = (now - timedelta(days=data_points - i - 1)).strftime("%a")
            elif period == "week":
                date = (now - timedelta(weeks=data_points - i - 1)).strftime("%Y-%m-%d")
                label = f"Week {i + 1}"
            elif period == "month":
                date = (now - timedelta(days=30 * (data_points - i - 1))).strftime("%Y-%m-%d")
                label = (now - timedelta(days=30 * (data_points - i - 1))).strftime("%b")
            else:  # quarter
                date = (now - timedelta(days=90 * (data_points - i - 1))).strftime("%Y-%m-%d")
                label = f"Q{i + 1}"
            
            # Generate growth trend with some randomness
            growth_factor = 1 + (i * 0.05) + (random.uniform(-0.1, 0.1))
            buyers = int(base_buyers * growth_factor)
            
            growth_data.append({
                "date": date,
                "label": label,
                "buyers": buyers,
                "growth_rate": round((growth_factor - 1) * 100, 1)
            })
        
        return {
            "success": True,
            "asin": asin,
            "period": period,
            "data": growth_data,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "data_points": len(growth_data),
                "note": "This is simulated data for demonstration"
            }
        }
    except Exception as e:
        print(f"Error generating growth data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    ai_mode = "openai" if OPENAI_AVAILABLE else ("nlp-only" if config.ENABLE_AI else "disabled")
    auth_mode = "supabase-only" if SUPABASE_AUTH_AVAILABLE else "disabled"
    return {
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "operational",
        "apify": "connected" if apify_client else "not configured",
        "ai": ai_mode,
        "auth": auth_mode,
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "analyze": "/api/v1/analyze",
            "growth": "/api/v1/growth/{asin}",
            "cache_results": "/api/v1/cache/results",
        }
    }

@app.get("/health")
async def health():
    """Health check"""
    ai_mode = "openai" if OPENAI_AVAILABLE else ("nlp-only" if config.ENABLE_AI else "disabled")
    auth_mode = "supabase-only" if SUPABASE_AUTH_AVAILABLE else "disabled"
    cache_diagnostics = (
        cache_service.diagnostics()
        if hasattr(cache_service, "diagnostics")
        else {
            "enabled": bool(getattr(cache_service, "enabled", False)),
            "backend": "unknown",
            "last_error": None,
        }
    )
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "operational",
            "apify": "connected" if apify_client else "not configured",
            "ai": ai_mode,
            "auth": auth_mode,
            "cache": "enabled" if bool(getattr(cache_service, "enabled", False)) else "disabled",
            "cache_backend": cache_diagnostics.get("backend", "unknown"),
            "cache_last_error": cache_diagnostics.get("last_error"),
        }
    }


@app.post("/api/v1/auth/signup")
async def signup():
    """Deprecated: signup is handled by Supabase Auth directly."""
    _reject_legacy_auth_route("POST /api/v1/auth/signup")


@app.post("/api/v1/auth/login")
async def login():
    """Deprecated: login is handled by Supabase Auth directly."""
    _reject_legacy_auth_route("POST /api/v1/auth/login")


@app.post("/api/v1/auth/logout")
async def logout():
    """Deprecated: logout is handled by Supabase Auth directly."""
    _reject_legacy_auth_route("POST /api/v1/auth/logout")


@app.post("/api/v1/auth/logout-all")
async def logout_all():
    """Deprecated: logout-all is handled by Supabase Auth directly."""
    _reject_legacy_auth_route("POST /api/v1/auth/logout-all")


@app.get("/api/v1/auth/csrf")
async def csrf():
    """Compatibility endpoint: CSRF is not used in bearer-token mode."""
    return {"success": True, "csrf_token": ""}


@app.get("/api/v1/auth/me")
async def me(current_user=Depends(get_current_user)):
    """Return authenticated user profile from bearer token."""
    return {
        "success": True,
        "user": _user_payload(current_user),
    }


@app.post("/api/v1/auth/verify-email/request")
async def verify_email_request():
    """Deprecated: email verification requests are handled by Supabase Auth directly."""
    _reject_legacy_auth_route("POST /api/v1/auth/verify-email/request")


@app.post("/api/v1/auth/verify-email/confirm")
async def verify_email_confirm():
    """Deprecated: email verification confirmation is handled by Supabase Auth directly."""
    _reject_legacy_auth_route("POST /api/v1/auth/verify-email/confirm")


@app.post("/api/v1/auth/password-reset/request")
async def password_reset_request():
    """Deprecated: password reset request is handled by Supabase Auth directly."""
    _reject_legacy_auth_route("POST /api/v1/auth/password-reset/request")


@app.post("/api/v1/auth/password-reset/confirm")
async def password_reset_confirm():
    """Deprecated: password reset confirmation is handled by Supabase Auth directly."""
    _reject_legacy_auth_route("POST /api/v1/auth/password-reset/confirm")


@app.get("/api/v1/cache/results")
async def get_cached_results(
    limit: int = 20,
    include_payload: bool = True,
    _current_user=Depends(require_verified_user),
):
    """Return recent cached analysis entries for inspection/reuse."""
    safe_limit = max(1, min(int(limit), 100))
    entries = cache_service.list_analysis_entries(limit=safe_limit, include_payload=include_payload)
    return {
        "success": True,
        "count": len(entries),
        "cache_enabled": bool(getattr(cache_service, "enabled", False)),
        "cache_backend": getattr(cache_service, "backend", "unknown"),
        "cache_last_error": getattr(cache_service, "last_error", None),
        "results": entries,
    }


@app.post("/api/v1/analyze")
async def analyze_product(
    request: Dict,
    _current_user=Depends(require_verified_user),
    _csrf=Depends(require_csrf),
):
    """Main analysis endpoint - FLAT response structure"""
    try:
        asin = normalize_asin(request.get("asin"))
        if not asin:
            raise HTTPException(status_code=400, detail="Valid ASIN or Amazon product URL is required")
        max_reviews = min(int(request.get("max_reviews", 50)), config.MAX_REVIEWS)
        enable_ai = request.get("enable_ai", config.ENABLE_AI)
        country = str(request.get("country", "IN")).upper().strip()

        logger.info(f"🔍 Analyzing ASIN: {asin}")

        cache_key = build_analysis_cache_key(asin, country, max_reviews, bool(enable_ai))
        cached_response = cache_service.get(cache_key)
        if cached_response and cached_response.get("success"):
            logger.info(f"⚡ Cache HIT for {cache_key}")
            cached_payload = dict(cached_response)
            cached_payload["from_cache"] = True
            growth_data_store[asin].append({
                "timestamp": datetime.utcnow().isoformat(),
                "review_count": cached_payload.get("total_reviews", 0),
                "rating": cached_payload.get("average_rating", 0)
            })
            return cached_payload

        logger.info(f"🧊 Cache MISS for {cache_key}")

        # Fetch reviews (Apify or mock)
        reviews_data = await fetch_apify_reviews(asin, max_reviews, country)

        if not reviews_data.get("success"):
            return reviews_data

        # AI/NLP analysis
        if enable_ai and reviews_data.get("reviews"):
            analysis = analyze_reviews(reviews_data["reviews"])
            reviews_data.update(analysis)

        # Store growth data point
        growth_data_store[asin].append({
            "timestamp": datetime.utcnow().isoformat(),
            "review_count": reviews_data.get("total_reviews", 0),
            "rating": reviews_data.get("average_rating", 0)
        })

        # ✅ RETURN FLAT STRUCTURE - NO NESTING
        response_payload = {
            "success": True,
            "asin": asin,
            "country": country,
            "product_info": reviews_data.get("product_info"),
            "total_reviews": reviews_data.get("total_reviews", 0),
            "average_rating": reviews_data.get("average_rating", 0),
            "rating_distribution": reviews_data.get("rating_distribution", {}),
            "sentiment_distribution": reviews_data.get("sentiment_distribution"),
            "reviews": reviews_data.get("reviews", []),
            "review_samples": reviews_data.get("review_samples"),
            "ai_enabled": enable_ai,
            "top_keywords": reviews_data.get("top_keywords", []),
            "themes": reviews_data.get("themes", []),
            "emotions": reviews_data.get("emotions"),
            "summaries": reviews_data.get("summaries"),
            "insights": reviews_data.get("insights", []),
            "data_source": reviews_data.get("data_source", "unknown"),
            "from_cache": False,
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time": reviews_data.get("processing_time")
        }

        cache_service.set(cache_key, response_payload)
        return response_payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/growth/{asin}")
async def get_growth(asin: str, period: str = "week"):
    """Get buyer growth data"""
    try:
        # Generate or retrieve growth data
        growth_data = generate_growth_data(asin, period)
        
        return {
            "success": True,
            "asin": asin,
            "period": period,
            "data": growth_data
        }
        
    except Exception as e:
        logger.error(f"Growth data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/insights")
async def generate_insights(request: Dict):
    """Generate insights from reviews"""
    try:
        reviews = request.get("reviews", [])
        if not reviews:
            raise HTTPException(status_code=400, detail="Reviews data required")

        analysis = analyze_reviews(reviews)

        return {
            "success": True,
            "insights": analysis.get("insights", []),
            "summary": analysis.get("summary", ""),
            "keywords": analysis.get("top_keywords", [])
        }

    except Exception as e:
        print(f"Insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/export/csv")
async def export_csv(
    request: Dict,
    _current_user=Depends(require_verified_user),
    _csrf=Depends(require_csrf),
):
    """Export analysis to CSV"""
    try:
        if not EXPORTER_AVAILABLE:
            raise HTTPException(status_code=503, detail="Export service not available")

        analysis_data = request.get("analysis_data")
        if not analysis_data:
            raise HTTPException(status_code=400, detail="Analysis data required")

        print(f"📊 Exporting CSV for ASIN: {analysis_data.get('asin', 'unknown')}")

        # Use exporter service
        result = exporter.export_to_csv(
            analysis_data=analysis_data,
            reviews=analysis_data.get("reviews", [])
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Export failed"))

        file_path = result.get("file_path")

        # Return file as download
        if os.path.exists(file_path):
            return FileResponse(
                file_path,
                media_type="text/csv",
                filename=os.path.basename(file_path)
            )
        else:
            raise HTTPException(status_code=500, detail="Export file not found")

    except HTTPException:
        raise
    except Exception as e:
        print(f"CSV export error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/export/pdf")
async def export_pdf(
    request: Dict,
    _current_user=Depends(require_verified_user),
    _csrf=Depends(require_csrf),
):
    """Export analysis to PDF"""
    try:
        if not EXPORTER_AVAILABLE:
            raise HTTPException(status_code=503, detail="Export service not available")

        analysis_data = request.get("analysis_data")
        if not analysis_data:
            raise HTTPException(status_code=400, detail="Analysis data required")

        print(f"📄 Exporting PDF for ASIN: {analysis_data.get('asin', 'unknown')}")

        # Use exporter service
        result = exporter.export_to_pdf(analysis_data=analysis_data)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Export failed"))

        file_path = result.get("file_path")

        # Return file as download
        if os.path.exists(file_path):
            return FileResponse(
                file_path,
                media_type="application/pdf",
                filename=os.path.basename(file_path)
            )
        else:
            raise HTTPException(status_code=500, detail="Export file not found")

    except HTTPException:
        raise
    except Exception as e:
        print(f"PDF export error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/admin/users")
async def admin_list_users(_admin=Depends(require_admin)):
    """Deprecated: local admin user listing is disabled in Supabase-only mode."""
    _reject_legacy_auth_route("GET /api/v1/admin/users")


@app.patch("/api/v1/admin/users/{user_id}/role")
async def admin_update_user_role(user_id: str, _admin=Depends(require_admin)):
    """Deprecated: local admin role mutation is disabled in Supabase-only mode."""
    _reject_legacy_auth_route(f"PATCH /api/v1/admin/users/{user_id}/role")


@app.get("/api/v1/admin/sessions")
async def admin_list_sessions(_admin=Depends(require_admin)):
    """Deprecated: local admin session listing is disabled in Supabase-only mode."""
    _reject_legacy_auth_route("GET /api/v1/admin/sessions")

# ============= ERROR HANDLERS =============

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found"}
    )

@app.exception_handler(500)
async def server_error(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# ============= RUN SERVER =============

def run_server():
    """CLI entrypoint for local/dev server startup."""
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info"
    )

if __name__ == "__main__":
    run_server()
