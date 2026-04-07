import pytest

import main
from main import (
    _extract_product_info,
    _iter_apify_review_rows,
    _normalize_apify_review,
    _parse_rating,
)


def test_parse_rating_handles_strings_and_numbers():
    assert _parse_rating("4.5 out of 5 stars") == 4.5
    assert _parse_rating("3") == 3.0
    assert _parse_rating(2) == 2.0
    assert _parse_rating(None) == 0.0


def test_iter_apify_review_rows_flattens_nested_reviews():
    dataset_items = [
        {
            "asin": "B000TEST01",
            "productTitle": "Test Product",
            "reviews": [
                {"reviewTitle": "Great", "reviewDescription": "Worked well", "reviewRating": "5"},
                {"reviewTitle": "Okay", "reviewDescription": "Average", "reviewRating": "3"},
            ],
        }
    ]

    rows = _iter_apify_review_rows(dataset_items)
    assert len(rows) == 2
    assert rows[0]["asin"] == "B000TEST01"
    assert rows[0]["reviewTitle"] == "Great"


def test_normalize_apify_review_supports_multiple_key_shapes():
    raw = {
        "id": "r1",
        "title": "Solid value",
        "text": "Battery lasts long enough",
        "rating": "4.0 out of 5 stars",
        "author": "Alex",
        "date": "2026-04-01",
        "verifiedPurchase": "true",
        "helpfulVotes": "12",
    }

    normalized = _normalize_apify_review(raw, idx=0)
    assert normalized is not None
    assert normalized["title"] == "Solid value"
    assert normalized["text"] == "Battery lasts long enough"
    assert normalized["rating"] == 4.0
    assert normalized["verified"] is True
    assert normalized["helpful_count"] == 12


def test_normalize_apify_review_reads_alternate_rating_keys():
    raw = {
        "reviewTitle": "Works fine",
        "reviewDescription": "As expected",
        "ratingScore": "5",
        "reviewAuthor": "Pat",
    }

    normalized = _normalize_apify_review(raw, idx=1)
    assert normalized is not None
    assert normalized["rating"] == 5.0


def test_normalize_apify_review_reads_nested_rating_object():
    raw = {
        "reviewTitle": "Nice",
        "reviewDescription": "Good quality",
        "reviewRating": {"score": 4},
    }

    normalized = _normalize_apify_review(raw, idx=2)
    assert normalized is not None
    assert normalized["rating"] == 4.0


def test_extract_product_info_falls_back_to_asin_defaults():
    product_info = _extract_product_info([], "B000TEST01")
    assert product_info["asin"] == "B000TEST01"
    assert product_info["title"] == "Product B000TEST01"


def test_extract_product_info_uses_product_name_field():
    dataset_items = [
        {
            "asin": "B000TEST01",
            "productName": "Wireless Earbuds Pro",
            "averageRating": "4.4 out of 5 stars",
            "totalReviews": "1200",
        }
    ]

    product_info = _extract_product_info(dataset_items, "B000TEST01")
    assert product_info["asin"] == "B000TEST01"
    assert product_info["title"] == "Wireless Earbuds Pro"


def test_extract_product_info_ignores_generic_review_title_for_product_name():
    dataset_items = [
        {
            "asin": "B000TEST01",
            "title": "Great quality and fast delivery",
            "reviewTitle": "Great quality and fast delivery",
            "reviewDescription": "Loved it",
        }
    ]

    product_info = _extract_product_info(dataset_items, "B000TEST01")
    assert product_info["asin"] == "B000TEST01"
    assert product_info["title"] == "Product B000TEST01"


@pytest.mark.asyncio
async def test_fetch_apify_reviews_returns_mock_when_client_missing(monkeypatch):
    monkeypatch.setattr(main, "apify_client", None)
    monkeypatch.setattr(main.config, "USE_MOCK_FALLBACK", True)

    result = await main.fetch_apify_reviews("B000TEST01", max_reviews=5, country="US")
    assert result["success"] is True
    assert result["data_source"] == "mock"
    assert len(result["reviews"]) == 5


@pytest.mark.asyncio
async def test_fetch_apify_reviews_returns_error_when_no_fallback(monkeypatch):
    monkeypatch.setattr(main, "apify_client", None)
    monkeypatch.setattr(main.config, "USE_MOCK_FALLBACK", False)

    result = await main.fetch_apify_reviews("B000TEST01", max_reviews=5, country="US")
    assert result["success"] is False
    assert "configured" in result["error"].lower()
