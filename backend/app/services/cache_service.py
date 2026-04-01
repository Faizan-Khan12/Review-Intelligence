"""Redis cache service with graceful fallback behavior."""

import json
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
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.enabled = enabled and bool(redis_url)
        self._client: Optional[Redis] = None

        if enabled and not redis_url:
            logger.warning("Cache is enabled but REDIS_URL is missing. Cache will be disabled.")

    def _get_client(self) -> Optional[Redis]:
        """Get or lazily initialize Redis client."""
        if not self.enabled:
            return None

        if self._client is not None:
            return self._client

        try:
            client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            client.ping()
            self._client = client
            return self._client
        except RedisError as exc:
            logger.warning(f"Redis unavailable. Falling back to no-cache mode: {exc}")
            self._client = None
            return None

    def get(self, key: str) -> Optional[Any]:
        """Get and deserialize JSON value from cache."""
        if not key:
            return None

        client = self._get_client()
        if client is None:
            return None

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

        client = self._get_client()
        if client is None:
            return False

        ttl = ttl_seconds or self.default_ttl
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

        client = self._get_client()
        if client is None:
            return False

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

    def list_analysis_entries(self, limit: int = 20, include_payload: bool = False) -> List[Dict[str, Any]]:
        """List cached analyze entries with optional payloads."""
        if limit <= 0:
            return []

        client = self._get_client()
        if client is None:
            return []

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
