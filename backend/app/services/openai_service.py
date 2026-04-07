"""
OpenAI Integration Service
Generates summaries and insights from review data.
"""

import os
import time
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI, APIConnectionError, APITimeoutError, APIStatusError, RateLimitError


class OpenAIService:
    """Service for OpenAI GPT-based analysis."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "500"))
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.4"))
        self.timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "45"))
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
        self.client = None

        if not self.api_key:
            print("OpenAI API key not configured")
            return

        try:
            self.client = OpenAI(api_key=self.api_key)
            print("OpenAI service initialized")
        except Exception as exc:
            print(f"OpenAI initialization failed: {exc}")
            self.client = None

    def is_available(self) -> bool:
        """Return whether OpenAI client is configured."""
        return self.client is not None

    def _chat(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        """Run chat completion with small retry logic for transient failures."""
        if not self.client:
            return ""

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    timeout=self.timeout_seconds,
                )
                content = response.choices[0].message.content
                return content.strip() if content else ""
            except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
            except APIStatusError as exc:
                last_error = exc
                # 5xx may be transient; 4xx is usually configuration/model.
                if getattr(exc, "status_code", 500) >= 500 and attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
            except Exception as exc:
                last_error = exc
                break

        if last_error:
            print(f"OpenAI request failed: {last_error}")
        return ""

    def generate_summary(
        self,
        reviews: List[Dict[str, Any]],
        product_info: Dict[str, Any],
        sentiment_dist: Dict[str, int],
    ) -> str:
        """Generate product summary using GPT, with deterministic fallback."""
        if not self.is_available() or not reviews:
            return self._fallback_summary(reviews, product_info, sentiment_dist)

        product_title = product_info.get("title", "Product")
        total_reviews = len(reviews)
        avg_rating = sum(float(r.get("rating", 0) or 0) for r in reviews) / total_reviews if total_reviews else 0

        sample_reviews = reviews[:10]
        review_texts = "\n".join(
            f"- Rating {float(r.get('rating', 0) or 0):.1f}/5: {self._trim_text(r.get('text', ''))}"
            for r in sample_reviews
        )

        prompt = (
            "Analyze these Amazon reviews and provide a concise executive summary.\n\n"
            f"Product: {product_title}\n"
            f"Total Reviews: {total_reviews}\n"
            f"Average Rating: {avg_rating:.2f}/5\n"
            f"Sentiment Counts: positive={sentiment_dist.get('positive', 0)}, "
            f"neutral={sentiment_dist.get('neutral', 0)}, "
            f"negative={sentiment_dist.get('negative', 0)}\n\n"
            f"Sample Reviews:\n{review_texts}\n\n"
            "Write 3-4 sentences covering overall sentiment, key strengths, key concerns, and a buyer recommendation."
        )

        summary = self._chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are a product analyst writing factual summaries from customer reviews.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
        )

        if summary:
            return summary
        return self._fallback_summary(reviews, product_info, sentiment_dist)

    def generate_insights(
        self,
        reviews: List[Dict[str, Any]],
        sentiment_dist: Dict[str, int],
        keywords: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate actionable insights using GPT, with deterministic fallback."""
        if not self.is_available() or not reviews:
            return self._fallback_insights(reviews, sentiment_dist, keywords)

        total = len(reviews)
        positive_pct = (sentiment_dist.get("positive", 0) / total * 100) if total else 0
        negative_pct = (sentiment_dist.get("negative", 0) / total * 100) if total else 0
        top_keywords = [kw.get("word", "") for kw in keywords[:10] if kw.get("word")]

        prompt = (
            "Generate exactly 5 short actionable insights from these product reviews.\n\n"
            f"Total Reviews: {total}\n"
            f"Positive Sentiment: {positive_pct:.1f}%\n"
            f"Negative Sentiment: {negative_pct:.1f}%\n"
            f"Top Keywords: {', '.join(top_keywords) if top_keywords else 'N/A'}\n\n"
            "Sample review snippets:\n"
            + "\n".join(f"- {self._trim_text(r.get('text', ''))}" for r in reviews[:6])
            + "\n\n"
            "Return a numbered list with 5 items. Keep each item under 140 characters."
        )

        raw = self._chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are a data analyst giving practical product improvement guidance.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=380,
        )

        insights = self._parse_insight_lines(raw)
        if insights:
            return insights[:5]
        return self._fallback_insights(reviews, sentiment_dist, keywords)

    @staticmethod
    def _trim_text(text: Any, max_len: int = 140) -> str:
        value = str(text or "").strip().replace("\n", " ")
        if len(value) <= max_len:
            return value
        return value[: max_len - 3] + "..."

    @staticmethod
    def _parse_insight_lines(raw: str) -> List[str]:
        if not raw:
            return []

        lines: List[str] = []
        for chunk in raw.split("\n"):
            line = chunk.strip()
            if not line:
                continue
            line = re.sub(r"^[-*•]\s*", "", line)
            line = re.sub(r"^\d+[.)]\s*", "", line)
            line = line.strip()
            if line:
                lines.append(line)

        # If the model returned a single paragraph, split by sentence boundaries.
        if len(lines) == 1 and ". " in lines[0]:
            lines = [part.strip() for part in lines[0].split(". ") if part.strip()]

        # Deduplicate while preserving order.
        deduped: List[str] = []
        seen = set()
        for line in lines:
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(line)
        return deduped

    def _fallback_summary(
        self,
        reviews: List[Dict[str, Any]],
        product_info: Dict[str, Any],
        sentiment_dist: Dict[str, int],
    ) -> str:
        total = len(reviews)
        if total == 0:
            return "No reviews are available yet for summary generation."

        positive = sentiment_dist.get("positive", 0)
        negative = sentiment_dist.get("negative", 0)
        positive_pct = (positive / total * 100) if total else 0
        avg_rating = sum(float(r.get("rating", 0) or 0) for r in reviews) / total if total else 0

        if positive_pct >= 75:
            sentiment_desc = "excellent customer satisfaction"
        elif positive_pct >= 60:
            sentiment_desc = "good customer satisfaction"
        elif positive_pct >= 40:
            sentiment_desc = "mixed customer feedback"
        else:
            sentiment_desc = "notable customer concerns"

        return (
            f"Based on {total} reviews, the product averages {avg_rating:.1f}/5 and shows {sentiment_desc}. "
            f"Positive feedback appears in {positive} reviews, while {negative} reviews highlight weaknesses. "
            f"Use the top themes and keywords to validate fit before purchase."
        )

    def _fallback_insights(
        self,
        reviews: List[Dict[str, Any]],
        sentiment_dist: Dict[str, int],
        keywords: List[Dict[str, Any]],
    ) -> List[str]:
        insights: List[str] = []
        total = len(reviews)
        if total == 0:
            return ["No review data available yet."]

        positive_pct = (sentiment_dist.get("positive", 0) / total * 100) if total else 0
        negative_pct = (sentiment_dist.get("negative", 0) / total * 100) if total else 0

        if positive_pct > 70:
            insights.append(f"Strong satisfaction: {positive_pct:.1f}% positive sentiment.")
        elif positive_pct > 50:
            insights.append(f"Moderate satisfaction: {positive_pct:.1f}% positive sentiment.")
        else:
            insights.append(f"Improvement needed: only {positive_pct:.1f}% positive sentiment.")

        if negative_pct > 30:
            insights.append(f"High dissatisfaction risk: {negative_pct:.1f}% negative sentiment.")

        if keywords:
            top_words = ", ".join(k.get("word", "") for k in keywords[:3] if k.get("word"))
            if top_words:
                insights.append(f"Most discussed topics: {top_words}.")

        avg_rating = sum(float(r.get("rating", 0) or 0) for r in reviews) / total if total else 0
        insights.append(f"Average rating is {avg_rating:.1f}/5 across {total} reviews.")

        if total < 20:
            insights.append("Low review volume; confidence in trend direction is limited.")
        elif total > 100:
            insights.append("Large review volume improves signal reliability.")

        return insights[:5]


# Singleton instance
openai_service = OpenAIService()
