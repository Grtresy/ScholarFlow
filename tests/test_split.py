from app.services.llm.text_splitter import split_markdown


def test_split_returns_chunks():
    md = "# Title\n\nSome paragraph text.\n\n## Section\nMore text here."
    chunks = split_markdown(md, max_chars=100)
    assert chunks, "Expected at least one chunk"
    assert all("text" in c for c in chunks)
