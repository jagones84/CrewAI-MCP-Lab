from src.services.pdf_generator import clean_text


def test_clean_text_removes_think_tags_and_payload():
    raw = "<think>\ninternal reasoning\n</think>\n\nFinal Answer: Hello world."

    cleaned = clean_text(raw)

    assert "<think>" not in cleaned
    assert "internal reasoning" not in cleaned
    assert cleaned == "Hello world."
