from app.services.openai_service import OpenAIService


def test_parse_insight_lines_handles_numbered_and_bulleted_text():
    raw = "1. Strong build quality\n2) Battery could improve\n- Good value"
    insights = OpenAIService._parse_insight_lines(raw)
    assert insights == [
        "Strong build quality",
        "Battery could improve",
        "Good value",
    ]


def test_parse_insight_lines_splits_single_paragraph():
    raw = "Strong quality. Average battery life. Great value"
    insights = OpenAIService._parse_insight_lines(raw)
    assert len(insights) >= 2
