"""
Amazon Review Intelligence - Production Backend
Real-time Apify Integration with AI/NLP Analysis
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import os
import asyncio
import json
import traceback
import re
from collections import defaultdict
from io import BytesIO
from sqlalchemy.orm import Session

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

# Import auth dependencies
try:
    from app.db.session import get_db
    from app.services.auth_service import auth_service
    AUTH_AVAILABLE = True
    print("✅ Auth service loaded")
except ImportError as e:
    AUTH_AVAILABLE = False
    print(f"⚠️ Auth service not available: {e}")

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
    
    # Features
    ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
    MAX_REVIEWS = int(os.getenv("MAX_REVIEWS_PER_REQUEST", "100"))
    USE_MOCK_FALLBACK = os.getenv("USE_MOCK_FALLBACK", "true").lower() == "true"

    # Auth/session
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "ari_session")
    SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE = os.getenv(
        "COOKIE_SAMESITE",
        "none" if ENVIRONMENT == "production" else "lax",
    ).lower()

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


def build_analysis_cache_key(asin: str, country: str, max_reviews: int, enable_ai: bool) -> str:
    """Build cache key for analysis endpoint response."""
    return f"analysis:{asin}:{country}:{max_reviews}:{int(bool(enable_ai))}"


def _cookie_secure_flag() -> bool:
    """Enable secure cookies in production by default."""
    if config.ENVIRONMENT == "production":
        return True
    return config.COOKIE_SECURE


def _cookie_samesite_value() -> str:
    """Resolve SameSite policy with production-safe defaults."""
    configured = (config.COOKIE_SAMESITE or "").lower().strip()
    if configured in {"lax", "strict", "none"}:
        return configured
    return "none" if config.ENVIRONMENT == "production" else "lax"


def _set_session_cookie(response: Response, token: str) -> None:
    """Set session cookie with consistent security attributes."""
    max_age = config.SESSION_TTL_HOURS * 3600
    samesite = _cookie_samesite_value()
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=max_age,
        path="/",
        secure=_cookie_secure_flag(),
        httponly=True,
        samesite=samesite,
    )


def _clear_session_cookie(response: Response) -> None:
    """Clear session cookie."""
    samesite = _cookie_samesite_value()
    response.delete_cookie(
        key=config.SESSION_COOKIE_NAME,
        path="/",
        secure=_cookie_secure_flag(),
        httponly=True,
        samesite=samesite,
    )


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Resolve current authenticated user from session cookie."""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    session_token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = auth_service.get_user_from_session_token(db, session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    return user

def extract_keywords(texts: List[str], top_n: int = 10) -> List[Dict]:
    """Extract keywords from texts"""
    from collections import Counter
    import re
    
    # Combine all texts
    combined = " ".join(texts).lower()
    
    # Simple tokenization
    words = re.findall(r'\b[a-z]+\b', combined)
    
    # Filter stopwords
    try:
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('english'))
    except:
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once'}
    
    words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Count frequencies
    word_freq = Counter(words)
    
    # Return top keywords
    return [
        {"word": word, "frequency": freq}
        for word, freq in word_freq.most_common(top_n)
    ]

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

async def fetch_apify_reviews(asin: str, max_reviews: int = 50, country: str = "US") -> Dict:
    """Fetch real reviews from Apify"""
    if not apify_client:
        logger.warning("Apify client not initialized, using mock data")
        return generate_mock_reviews(asin, max_reviews)
    
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
            "filterByRatings": ["allStars"],
            "scrapeProductDetails": True
        }
        
        # Run the actor
        logger.info(f"🚀 Starting Apify actor: {config.APIFY_ACTOR_ID}")
        run = await asyncio.to_thread(
            apify_client.actor(config.APIFY_ACTOR_ID).call,
            run_input=actor_input,
            wait_secs=60  # Wait up to 60 seconds
        )
        
        # Get results
        dataset_items = []
        if run.get("defaultDatasetId"):
            dataset_client = apify_client.dataset(run["defaultDatasetId"])
            dataset_items = list(dataset_client.iterate_items())
        
        if not dataset_items:
            logger.warning("No data returned from Apify")
            if config.USE_MOCK_FALLBACK:
                return generate_mock_reviews(asin, max_reviews)
            return {"success": False, "error": "No data from Apify"}
        
        # Process results
        all_reviews = []
        product_info = {}
        
        for item in dataset_items:
            # Get product info once
            if not product_info and "productTitle" in item:
                product_info = {
                    "title": item.get("productTitle", ""),
                    "brand": item.get("brand", ""),
                    "price": item.get("price", ""),
                    "image": item.get("thumbnailImage", ""),
                    "rating": item.get("averageRating", 0),
                    "total_reviews": item.get("totalReviews", 0),
                    "asin": item.get("asin", asin)
                }
    
                # ✅ FIX: Each item IS a review!
            if "reviewTitle" in item or "reviewDescription" in item:
                try:
                    rating_str = item.get("reviewRating", "0")
                    if isinstance(rating_str, str) and "out of" in rating_str:
                        rating = float(rating_str.split()[0])
                    else:
                        rating = float(rating_str) if rating_str else 0
            
                    review = {
                        "id": item.get("id", ""),
                        "title": item.get("reviewTitle", ""),
                        "text": item.get("reviewDescription", ""),
                        "rating": rating,
                        "author": item.get("reviewAuthor", "Anonymous"),
                        "date": item.get("reviewDate", ""),
                        "verified": item.get("isVerified", False),
                        "helpful_count": item.get("helpfulCount", 0)
                    }
            
                    all_reviews.append(review)
                    logger.info(f"✅ Review: {review['title'][:40]}...")
            
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue
        
        if not all_reviews:
            logger.warning("No reviews extracted from Apify data")
            if config.USE_MOCK_FALLBACK:
                return generate_mock_reviews(asin, max_reviews)
        
        # Calculate statistics
        ratings = [r['rating'] for r in all_reviews]
        
        logger.info(f"✅ Successfully fetched {len(all_reviews)} reviews from Apify")
        
        return {
            "success": True,
            "asin": asin,
            "reviews": all_reviews[:max_reviews],
            "total_reviews": len(all_reviews),
            "average_rating": sum(ratings) / len(ratings) if ratings else 0,
            "rating_distribution": {
                "5": len([r for r in ratings if r >= 4.5]),
                "4": len([r for r in ratings if 3.5 <= r < 4.5]),
                "3": len([r for r in ratings if 2.5 <= r < 3.5]),
                "2": len([r for r in ratings if 1.5 <= r < 2.5]),
                "1": len([r for r in ratings if r < 1.5])
            },
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

# backend/main.py - REPLACE extract_themes function (around line 467)
def extract_themes(texts: List[str], sentiment_counts: dict) -> List[Dict[str, Any]]:
    """
    Extract themes from review texts using sklearn clustering
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import KMeans
        
        if len(texts) < 5:
            return simple_theme_extraction(texts)
        
        vectorizer = TfidfVectorizer(max_features=50, stop_words='english', ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        n_clusters = min(5, len(texts))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(tfidf_matrix)
        
        feature_names = vectorizer.get_feature_names_out()
        themes = []
        
        for cluster_id in range(n_clusters):
            cluster_center = kmeans.cluster_centers_[cluster_id]
            top_indices = cluster_center.argsort()[-3:][::-1]
            theme_words = [feature_names[i] for i in top_indices]
            theme_name = " ".join(theme_words[:2]).title()
            
            mentions = sum(1 for label in kmeans.labels_ if label == cluster_id)
            
            # Simple sentiment detection
            sentiment = "neutral"
            if "good" in theme_name.lower() or "great" in theme_name.lower():
                sentiment = "positive"
            elif "bad" in theme_name.lower() or "poor" in theme_name.lower():
                sentiment = "negative"
            
            themes.append({
                "theme": theme_name,
                "mentions": mentions,
                "sentiment": sentiment
            })
        
        return sorted(themes, key=lambda x: x["mentions"], reverse=True)
        
    except Exception as e:
        logger.warning(f"sklearn clustering failed: {e}, using simple extraction")
        return simple_theme_extraction(texts)


def simple_theme_extraction(texts: List[str]) -> List[Dict[str, Any]]:
    """
    Simple theme extraction without sklearn - FIXED
    """
    theme_keywords = {
        "Quality": ["quality", "build", "material", "durable", "sturdy", "well made"],
        "Price": ["price", "expensive", "cheap", "value", "worth", "cost"],
        "Performance": ["performance", "works", "fast", "slow", "efficient", "speed"],
        "Delivery": ["delivery", "shipping", "arrived", "packaging", "package"],
        "Design": ["design", "look", "appearance", "style", "color", "beautiful"],
        "Size": ["size", "fit", "large", "small", "perfect fit"],
        "Easy to Use": ["easy", "simple", "convenient", "user friendly", "straightforward"],
    }
    
    themes = []
    
    for theme_name, keywords in theme_keywords.items():
        mentions = sum(1 for text in texts if any(kw in text.lower() for kw in keywords))
        
        if mentions > 0:
            # Find theme texts
            theme_texts = [text for text in texts if any(kw in text.lower() for kw in keywords)]
            
            # Simple sentiment
            positive_words = ['great', 'good', 'excellent', 'amazing', 'love', 'perfect', 'best']
            negative_words = ['bad', 'poor', 'terrible', 'waste', 'disappointed', 'not good']
            
            sentiment_scores = []
            for text_lower in [t.lower() for t in theme_texts]:
                pos = sum(1 for w in positive_words if w in text_lower)
                neg = sum(1 for w in negative_words if w in text_lower)
                if pos > neg:
                    sentiment_scores.append('positive')
                elif neg > pos:
                    sentiment_scores.append('negative')
                else:
                    sentiment_scores.append('neutral')
            
            sentiment = max(set(sentiment_scores), key=sentiment_scores.count) if sentiment_scores else "neutral"
            
            themes.append({
                "theme": theme_name,
                "mentions": mentions,
                "sentiment": sentiment
            })
    
    return sorted(themes, key=lambda x: x["mentions"], reverse=True)[:5]


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
    return {
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "operational",
        "apify": "connected" if apify_client else "not configured",
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
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "operational",
            "apify": "connected" if apify_client else "not configured",
            "ai": "enabled" if config.ENABLE_AI else "disabled"
        }
    }


@app.post("/api/v1/auth/signup")
async def signup(request: Dict, response: Response, db: Session = Depends(get_db)):
    """Register user and create session cookie."""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    email = str(request.get("email", "")).strip().lower()
    password = str(request.get("password", ""))

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    try:
        user = auth_service.create_user(db, email, password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    session_token = auth_service.create_session(db, user.id, config.SESSION_TTL_HOURS)
    _set_session_cookie(response, session_token)

    return {
        "success": True,
        "message": "Signup successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
        },
    }


@app.post("/api/v1/auth/login")
async def login(request: Dict, response: Response, db: Session = Depends(get_db)):
    """Authenticate user and create session cookie."""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    email = str(request.get("email", "")).strip().lower()
    password = str(request.get("password", ""))

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = auth_service.authenticate_user(db, email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session_token = auth_service.create_session(db, user.id, config.SESSION_TTL_HOURS)
    _set_session_cookie(response, session_token)

    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
        },
    }


@app.post("/api/v1/auth/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Revoke current session and clear cookie."""
    if not AUTH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    session_token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if session_token:
        auth_service.revoke_session(db, session_token)

    _clear_session_cookie(response)
    return {"success": True, "message": "Logout successful"}


@app.get("/api/v1/auth/me")
async def me(current_user=Depends(get_current_user)):
    """Return authenticated user profile from session cookie."""
    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "is_active": current_user.is_active,
        },
    }


@app.get("/api/v1/cache/results")
async def get_cached_results(
    limit: int = 20,
    include_payload: bool = True,
    _current_user=Depends(get_current_user),
):
    """Return recent cached analysis entries for inspection/reuse."""
    safe_limit = max(1, min(int(limit), 100))
    entries = cache_service.list_analysis_entries(limit=safe_limit, include_payload=include_payload)
    return {
        "success": True,
        "count": len(entries),
        "cache_enabled": bool(getattr(cache_service, "enabled", False)),
        "results": entries,
    }


@app.post("/api/v1/analyze")
async def analyze_product(request: Dict, _current_user=Depends(get_current_user)):
    """Main analysis endpoint - FLAT response structure"""
    try:
        asin = request.get("asin")
        if not asin:
            raise HTTPException(status_code=400, detail="ASIN is required")

        asin = str(asin).strip()
        max_reviews = min(int(request.get("max_reviews", 50)), config.MAX_REVIEWS)
        enable_ai = request.get("enable_ai", config.ENABLE_AI)
        country = str(request.get("country", "US")).upper().strip()

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
async def export_csv(request: Dict, _current_user=Depends(get_current_user)):
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
async def export_pdf(request: Dict, _current_user=Depends(get_current_user)):
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
