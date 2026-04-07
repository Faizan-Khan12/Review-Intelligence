from typing import Dict, List

from app.services.cache_service import RedisCacheService


class FakeRedis:
    def __init__(self):
        self.data: Dict[str, str] = {}
        self.ttls: Dict[str, int] = {}

    def get(self, key: str):
        return self.data.get(key)

    def setex(self, key: str, ttl: int, value: str):
        self.data[key] = value
        self.ttls[key] = ttl

    def delete(self, key: str):
        if key in self.data:
            del self.data[key]
            self.ttls.pop(key, None)
            return 1
        return 0

    def scan_iter(self, match: str = "*", count: int = 10):
        prefix = match.replace("*", "")
        keys: List[str] = [k for k in self.data.keys() if k.startswith(prefix)]
        for key in keys:
            yield key


def _service_with_fake_client(default_ttl: int = 172800):
    service = RedisCacheService(
        redis_url="redis://localhost:6379/0",
        default_ttl=default_ttl,
        enabled=True,
    )
    fake = FakeRedis()
    service._get_client = lambda: fake  # type: ignore[method-assign]
    return service, fake


def test_cache_set_get_uses_default_ttl():
    service, fake = _service_with_fake_client(default_ttl=172800)

    ok = service.set("analysis:B000TEST01:US:50:1", {"success": True, "value": 1})
    assert ok is True
    assert fake.ttls["analysis:B000TEST01:US:50:1"] == 172800

    cached = service.get("analysis:B000TEST01:US:50:1")
    assert cached is not None
    assert cached["success"] is True
    assert cached["value"] == 1


def test_list_analysis_entries_parses_keys_and_payloads():
    service, _fake = _service_with_fake_client(default_ttl=172800)

    service.set(
        "analysis:B000TEST01:US:50:1",
        {
            "success": True,
            "total_reviews": 50,
            "average_rating": 4.3,
            "timestamp": "2026-04-06T10:00:00",
            "data_source": "apify",
        },
    )
    service.set(
        "analysis:B000TEST02:IN:100:0",
        {
            "success": True,
            "total_reviews": 100,
            "average_rating": 3.9,
            "timestamp": "2026-04-06T11:00:00",
            "data_source": "apify",
        },
    )

    entries = service.list_analysis_entries(limit=10, include_payload=True)
    assert len(entries) == 2
    assert entries[0]["asin"] == "B000TEST02"
    assert entries[0]["product_title"] == "Product B000TEST02"
    assert entries[0]["enable_ai"] is False
    assert entries[0]["analysis"]["success"] is True


def test_list_analysis_entries_uses_cached_product_title():
    service, _fake = _service_with_fake_client(default_ttl=172800)

    service.set(
        "analysis:B000TITLE01:IN:50:1",
        {
            "success": True,
            "product_info": {"title": "Super Blender 9000"},
            "total_reviews": 42,
            "average_rating": 4.1,
            "timestamp": "2026-04-06T10:00:00",
            "data_source": "apify",
        },
    )

    entries = service.list_analysis_entries(limit=10, include_payload=False)
    assert len(entries) == 1
    assert entries[0]["asin"] == "B000TITLE01"
    assert entries[0]["product_title"] == "Super Blender 9000"


def test_cache_disabled_without_redis_url():
    service = RedisCacheService(redis_url="", default_ttl=172800, enabled=True)
    assert service.enabled is False
    assert service.get("analysis:any") is None
    assert service.set("analysis:any", {"success": True}) is False


def test_memory_fallback_when_redis_unavailable():
    service = RedisCacheService(
        redis_url="rediss://default:pass@unresolvable-host.upstash.io:6379",
        default_ttl=120,
        enabled=True,
    )

    key = "analysis:B000MEM001:IN:50:1"
    payload = {"success": True, "total_reviews": 12, "average_rating": 4.2, "timestamp": "2026-04-06T10:00:00"}
    assert service.set(key, payload) is True

    cached = service.get(key)
    assert cached is not None
    assert cached["success"] is True
    assert service.backend == "memory"

    listed = service.list_analysis_entries(limit=10, include_payload=False)
    assert len(listed) == 1
    assert listed[0]["asin"] == "B000MEM001"

    diagnostics = service.diagnostics()
    assert diagnostics["enabled"] is True
    assert diagnostics["backend"] == "memory"
