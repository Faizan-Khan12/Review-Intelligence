import main


def test_extract_keywords_prefers_meaningful_phrases_over_generic_words():
    texts = [
        "Great product with excellent sound quality and strong noise cancellation.",
        "The sound quality is clear and battery life lasts all day.",
        "Noise cancellation and battery life are the main reasons I bought these headphones.",
        "Build quality feels premium and connection setup is easy.",
        "Good value for money but shipping was late.",
        "Battery life and sound quality are much better than my previous pair.",
    ]

    keywords = main.extract_keywords(texts, top_n=10)
    words = [str(item.get("word", "")).lower() for item in keywords]

    # Low-value filler terms should be removed.
    assert "great" not in words
    assert "good" not in words
    assert "product" not in words
    assert "value" not in words
    assert "money" not in words

    # High-signal review terms should survive.
    assert any("sound quality" in word for word in words)
    assert any("battery life" in word for word in words)
    assert any("noise cancellation" in word for word in words)


def test_extract_themes_returns_canonical_high_value_labels():
    texts = [
        "Sound quality is excellent and noise cancellation blocks office chatter.",
        "Battery life easily lasts a full workday.",
        "Comfort and fit are good for long listening sessions.",
        "Bluetooth connection drops sometimes and the app is buggy.",
        "Packaging was clean and delivery arrived on time.",
        "The build quality feels durable and premium.",
    ]

    themes = main.extract_themes(texts, sentiment_counts={})
    names = [str(item.get("theme", "")) for item in themes]

    assert "Sound Quality" in names
    assert "Battery Life" in names
    assert "Noise Cancellation" in names

    # Prevent low-value cluster labels like "Quality Okay" / "Money Value Money".
    joined = " ".join(names).lower()
    assert "okay" not in joined
    assert "money value money" not in joined
