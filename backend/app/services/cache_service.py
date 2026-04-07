"""Redis cache service with graceful fallback behavior."""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class RedisCacheService:
    """Wrapper around Redis operations used by the application."""

    def __init__(
        self,
        redis_url: str,
        default_ttl: int,
        enabled: bool,
    ) -> None:
        self.redis_url = self._normalize_redis_url(redis_url)
        self.default_ttl = default_ttl
        self.enabled = enabled and bool(redis_url)
        self._client: Optional[Redis] = None
        self.backend = "disabled" if not self.enabled else "redis"
        self.last_error: Optional[str] = None
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._retry_after_epoch = 0.0
        self._retry_interval_seconds = 30

        if enabled and not redis_url:
            logger.warning("Cache is enabled but REDIS_URL is missing. Cache will be disabled.")

    @staticmethod
    def _normalize_redis_url(redis_url: str) -> str:
        """Normalize Redis URL and auto-apply default scheme when omitted."""
        value = (redis_url or "").strip()
        if not value:
            return value
        if "://" in value:
            return value
        logger.warning("REDIS_URL missing scheme. Assuming redis://")
        return f"redis://{value}"

    def _get_client(self) -> Optional[Redis]:
        """Get or lazily initialize Redis client."""
        if not self.enabled:
            self.backend = "disabled"
            return None

        if self._client is not None:
            self.backend = "redis"
            return self._client

        now = time.time()
        if now < self._retry_after_epoch:
            self.backend = "memory"
            return None

        try:
            client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            client.ping()
            self._client = client
            self.backend = "redis"
            self.last_error = None
            return self._client
        except (RedisError, ValueError, TypeError) as exc:
            self.backend = "memory"
            self.last_error = str(exc)
            self._retry_after_epoch = time.time() + self._retry_interval_seconds
            logger.warning(f"Redis unavailable. Falling back to memory cache mode: {exc}")
            self._client = None
            return None
        except Exception as exc:  # pragma: no cover - defensive
            self.backend = "memory"
            self.last_error = str(exc)
            self._retry_after_epoch = time.time() + self._retry_interval_seconds
            logger.warning(f"Unexpected Redis initialization error. Falling back to memory cache mode: {exc}")
            self._client = None
            return None

    def _memory_get(self, key: str) -> Optional[Any]:
        entry = self._memory_store.get(key)
        if not entry:
            return None

        expires_at = float(entry.get("expires_at", 0))
        if expires_at and expires_at <= time.time():
            self._memory_store.pop(key, None)
            return None

        try:
            return json.loads(entry.get("payload", "null"))
        except (TypeError, ValueError):
            self._memory_store.pop(key, None)
            return None

    def _memory_set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        try:
            serialized = json.dumps(value, default=str)
            self._memory_store[key] = {
                "expires_at": time.time() + max(1, int(ttl_seconds)),
                "payload": serialized,
            }
            return True
        except (TypeError, ValueError) as exc:
            logger.warning(f"Memory cache SET failed for key '{key}': {exc}")
            return False

    def _memory_delete(self, key: str) -> bool:
        return bool(self._memory_store.pop(key, None))

    def _memory_list_analysis_entries(self, limit: int, include_payload: bool) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for key in list(self._memory_store.keys()):
            parsed = self._parse_analysis_key(key)
            if not parsed:
                continue

            cached = self._memory_get(key)
            if not cached or not isinstance(cached, dict):
                continue

            asin, country, max_reviews, enable_ai = parsed
            entry: Dict[str, Any] = {
                "key": key,
                "asin": asin,
                "product_title": self._extract_product_title(cached, asin),
                "country": country,
                "max_reviews": max_reviews,
                "enable_ai": enable_ai,
                "total_reviews": cached.get("total_reviews", 0),
                "average_rating": cached.get("average_rating", 0),
                "timestamp": cached.get("timestamp"),
                "data_source": cached.get("data_source", "unknown"),
            }
            if include_payload:
                entry["analysis"] = cached
            entries.append(entry)

        def sort_key(item: Dict[str, Any]) -> datetime:
            ts = item.get("timestamp")
            if not ts:
                return datetime.min
            try:
                return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except ValueError:
                return datetime.min

        entries.sort(key=sort_key, reverse=True)
        return entries[:limit]

    def diagnostics(self) -> Dict[str, Any]:
        """Expose cache diagnostics for health/debug endpoints."""
        return {
            "enabled": self.enabled,
            "backend": self.backend,
            "redis_configured": bool(self.redis_url),
            "memory_entries": len(self._memory_store),
            "last_error": self.last_error,
        }

    def get(self, key: str) -> Optional[Any]:
        """Get and deserialize JSON value from cache."""
        if not key:
            return None
        if not self.enabled:
            return None

        client = self._get_client()
        if client is None:
            return self._memory_get(key)

        try:
            raw_value = client.get(key)
            if raw_value is None:
                return None
            return json.loads(raw_value)
        except (RedisError, json.JSONDecodeError, TypeError) as exc:
            logger.warning(f"Cache GET failed for key '{key}': {exc}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Serialize and store JSON value in cache."""
        if not key:
            return False
        if not self.enabled:
            return False

        client = self._get_client()
        ttl = ttl_seconds or self.default_ttl
        if client is None:
            return self._memory_set(key, value, ttl)

        try:
            serialized = json.dumps(value, default=str)
            client.setex(key, ttl, serialized)
            return True
        except (RedisError, TypeError, ValueError) as exc:
            logger.warning(f"Cache SET failed for key '{key}': {exc}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a cache key."""
        if not key:
            return False
        if not self.enabled:
            return False

        client = self._get_client()
        if client is None:
            return self._memory_delete(key)

        try:
            return bool(client.delete(key))
        except RedisError as exc:
            logger.warning(f"Cache DELETE failed for key '{key}': {exc}")
            return False

    @staticmethod
    def _parse_analysis_key(key: str) -> Optional[Tuple[str, str, int, bool]]:
        """Parse `analysis:{asin}:{country}:{max_reviews}:{enable_ai}` key format."""
        parts = key.split(":")
        if len(parts) != 5 or parts[0] != "analysis":
            return None
        _, asin, country, max_reviews_raw, enable_ai_raw = parts
        try:
            max_reviews = int(max_reviews_raw)
            enable_ai = bool(int(enable_ai_raw))
        except ValueError:
            return None
        return asin, country, max_reviews, enable_ai

    @staticmethod
    def _extract_product_title(cached: Dict[str, Any], asin: str) -> str:
        """Extract product title from cached analysis payload with stable fallback."""
        product_info = cached.get("product_info")
        if isinstance(product_info, dict):
            title = product_info.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
        return f"Product {asin}"

    def list_analysis_entries(self, limit: int = 20, include_payload: bool = False) -> List[Dict[str, Any]]:
        """List cached analyze entries with optional payloads."""
        if limit <= 0:
            return []
        if not self.enabled:
            return []

        client = self._get_client()
        if client is None:
            return self._memory_list_analysis_entries(limit=limit, include_payload=include_payload)

        entries: List[Dict[str, Any]] = []
        try:
            for key in client.scan_iter(match="analysis:*", count=min(max(limit * 5, 50), 1000)):
                parsed = self._parse_analysis_key(key)
                if not parsed:
                    continue

                cached = self.get(key)
                if not cached or not isinstance(cached, dict):
                    continue

                asin, country, max_reviews, enable_ai = parsed
                entry: Dict[str, Any] = {
                    "key": key,
                    "asin": asin,
                    "product_title": self._extract_product_title(cached, asin),
                    "country": country,
                    "max_reviews": max_reviews,
                    "enable_ai": enable_ai,
                    "total_reviews": cached.get("total_reviews", 0),
                    "average_rating": cached.get("average_rating", 0),
                    "timestamp": cached.get("timestamp"),
                    "data_source": cached.get("data_source", "unknown"),
                }
                if include_payload:
                    entry["analysis"] = cached
                entries.append(entry)

            def sort_key(item: Dict[str, Any]) -> datetime:
                ts = item.get("timestamp")
                if not ts:
                    return datetime.min
                try:
                    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                except ValueError:
                    return datetime.min

            entries.sort(key=sort_key, reverse=True)
            return entries[:limit]
        except RedisError as exc:
            logger.warning(f"Cache LIST failed: {exc}")
            return []


cache_service = RedisCacheService(
    redis_url=settings.REDIS_URL,
    default_ttl=settings.REDIS_TTL_SECONDS,
    enabled=settings.ENABLE_CACHE,
)
