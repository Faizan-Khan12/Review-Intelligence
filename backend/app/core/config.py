"""
Application Configuration
Central configuration management with environment variables
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings with environment variable management"""
    
    # ============= APPLICATION =============
    APP_NAME: str = os.getenv("APP_NAME", "Amazon Review Intelligence")
    APP_VERSION: str = os.getenv("APP_VERSION", "2.0.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # ============= SERVER =============
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # ============= CORS =============
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://amazon-review-intelligence.vercel.app"
    ).split(",")
    ALLOW_CREDENTIALS: bool = os.getenv("ALLOW_CREDENTIALS", "true").lower() == "true"
    ALLOW_METHODS: str = os.getenv("ALLOW_METHODS", "*")
    ALLOW_HEADERS: str = os.getenv("ALLOW_HEADERS", "*")
    
    # ============= DATA SOURCE =============
    DATA_SOURCE: str = os.getenv("DATA_SOURCE", "apify").lower()  # apify, mock, hybrid
    MAX_REVIEWS_PER_REQUEST: int = int(os.getenv("MAX_REVIEWS_PER_REQUEST", "100"))
    USE_MOCK_FALLBACK: bool = os.getenv("USE_MOCK_FALLBACK", "true").lower() == "true"
    
    # ============= APIFY =============
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    APIFY_ACTOR_ID: str = os.getenv("APIFY_ACTOR_ID", "junglee/amazon-reviews-scraper")
    APIFY_TIMEOUT_SECONDS: int = int(os.getenv("APIFY_TIMEOUT_SECONDS", "300"))
    
    # ============= AI/NLP =============
    ENABLE_AI: bool = os.getenv("ENABLE_AI", "true").lower() == "true"
    ENABLE_EMOTIONS: bool = os.getenv("ENABLE_EMOTIONS", "true").lower() == "true"
    ENABLE_THEME_EXTRACTION: bool = os.getenv("ENABLE_THEME_EXTRACTION", "true").lower() == "true"
    ENABLE_KEYWORD_CLUSTERING: bool = os.getenv("ENABLE_KEYWORD_CLUSTERING", "true").lower() == "true"
    ENABLE_INSIGHTS_GENERATION: bool = os.getenv("ENABLE_INSIGHTS_GENERATION", "true").lower() == "true"
    
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "free").lower()  # free, openai, huggingface, transformers, hybrid
    
    # ============= OPENAI (Optional) =============
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "500"))
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # ============= HUGGING FACE (Optional) =============
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")
    HUGGINGFACE_MODEL: str = os.getenv("HUGGINGFACE_MODEL", "distilbert-base-uncased-finetuned-sst-2-english")
    
    # ============= DATABASE =============
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    USE_DATABASE: bool = os.getenv("USE_DATABASE", "false").lower() == "true"
    
    # ============= REDIS CACHE =============
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    REDIS_TTL_SECONDS: int = int(os.getenv("REDIS_TTL_SECONDS", "172800"))
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "false").lower() == "true"

    # ============= SUPABASE AUTH =============
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_AUTH_TIMEOUT_SECONDS: int = int(os.getenv("SUPABASE_AUTH_TIMEOUT_SECONDS", "5"))
    SUPABASE_AUTH_CACHE_TTL_SECONDS: int = int(os.getenv("SUPABASE_AUTH_CACHE_TTL_SECONDS", "60"))
    
    # ============= SECURITY =============
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # ============= RATE LIMITING =============
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
    
    # ============= FEATURES =============
    ENABLE_EXPORT_PDF: bool = os.getenv("ENABLE_EXPORT_PDF", "true").lower() == "true"
    ENABLE_EXPORT_EXCEL: bool = os.getenv("ENABLE_EXPORT_EXCEL", "true").lower() == "true"
    ENABLE_BUYER_GROWTH_TRACKING: bool = os.getenv("ENABLE_BUYER_GROWTH_TRACKING", "true").lower() == "true"
    ENABLE_REAL_TIME_UPDATES: bool = os.getenv("ENABLE_REAL_TIME_UPDATES", "true").lower() == "true"
    ENABLE_MULTI_COUNTRY_SEARCH: bool = os.getenv("ENABLE_MULTI_COUNTRY_SEARCH", "true").lower() == "true"

    # ============= EXPORT =============
    EXPORT_FOLDER: str = os.getenv("EXPORT_FOLDER", "/tmp/exports")
    
    # ============= PERFORMANCE =============
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "50"))
    ENABLE_ASYNC_PROCESSING: bool = os.getenv("ENABLE_ASYNC_PROCESSING", "true").lower() == "true"
    
    # ============= MOCK DATA =============
    MOCK_DATA_MIN_REVIEWS: int = int(os.getenv("MOCK_DATA_MIN_REVIEWS", "10"))
    MOCK_DATA_MAX_REVIEWS: int = int(os.getenv("MOCK_DATA_MAX_REVIEWS", "100"))
    MOCK_DATA_DEFAULT_REVIEWS: int = int(os.getenv("MOCK_DATA_DEFAULT_REVIEWS", "50"))
    MOCK_PRODUCT_VARIATIONS: bool = os.getenv("MOCK_PRODUCT_VARIATIONS", "true").lower() == "true"
    
    # ============= MONITORING =============
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", "development")
    
    # ============= EMAIL (Optional) =============
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@yourdomain.com")
    ENABLE_EMAIL_NOTIFICATIONS: bool = os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "false").lower() == "true"
    
    # ============= AWS S3 (Optional) =============
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_S3_BUCKET_NAME: str = os.getenv("AWS_S3_BUCKET_NAME", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    USE_S3_STORAGE: bool = os.getenv("USE_S3_STORAGE", "false").lower() == "true"
    
    # ============= WEBHOOKS (Optional) =============
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    ENABLE_WEBHOOKS: bool = os.getenv("ENABLE_WEBHOOKS", "false").lower() == "true"

     

    # ============= EXPORT =============

    EXPORT_FOLDER: str = os.getenv("EXPORT_FOLDER", "/tmp/exports")
    
    # ============= HELPER METHODS =============
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"
    
    def is_using_mock_data(self) -> bool:
        """Check if using mock data"""
        return self.DATA_SOURCE == "mock"
    
    def is_using_apify(self) -> bool:
        """Check if using Apify"""
        return self.DATA_SOURCE == "apify" and bool(self.APIFY_API_TOKEN)
    
    def has_openai(self) -> bool:
        """Check if OpenAI is configured"""
        return bool(self.OPENAI_API_KEY)
    
    def has_database(self) -> bool:
        """Check if database is configured"""
        return bool(self.DATABASE_URL) and self.USE_DATABASE
    
    def has_redis(self) -> bool:
        """Check if Redis is configured"""
        return bool(self.REDIS_URL) and self.ENABLE_CACHE

    def has_supabase_auth(self) -> bool:
        """Check if Supabase auth is configured."""
        return bool(self.SUPABASE_URL and self.SUPABASE_ANON_KEY)
    
    def get_data_source_info(self) -> dict:
        """Get data source configuration info"""
        return {
            "data_source": self.DATA_SOURCE,
            "using_mock": self.is_using_mock_data(),
            "apify_configured": bool(self.APIFY_API_TOKEN),
            "openai_configured": self.has_openai(),
            "ai_enabled": self.ENABLE_AI,
            "emotions_enabled": self.ENABLE_EMOTIONS,
            "database_configured": self.has_database(),
            "cache_configured": self.has_redis(),
            "supabase_auth_configured": self.has_supabase_auth(),
        }
    
    def validate(self):
        """Validate configuration and print warnings"""
        warnings = []
        
        # Check data source
        if self.DATA_SOURCE == "apify" and not self.APIFY_API_TOKEN:
            warnings.append("DATA_SOURCE is 'apify' but APIFY_API_TOKEN is not set")
            self.DATA_SOURCE = "mock"  # Fallback to mock
        
        # Check AI provider
        if self.AI_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            warnings.append("AI_PROVIDER is 'openai' but OPENAI_API_KEY is not set")
            self.AI_PROVIDER = "free"  # Fallback to free
        
        # Check security
        if self.is_production() and self.SECRET_KEY == "your-super-secret-key-change-this":
            warnings.append("⚠️ CRITICAL: Using default SECRET_KEY in production!")
        
        # Print warnings
        if warnings:
            print("=" * 60)
            print("⚠️ Configuration Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
            print("=" * 60)
        
        return len(warnings) == 0


# Create singleton instance
settings = Settings()

# Validate on import
settings.validate()
