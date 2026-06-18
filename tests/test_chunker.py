from app.rag.chunker import recursive_character_splitter


def test_recursive_character_splitter_respects_size_and_overlap():
    text = "第一段。" * 200
    chunks = recursive_character_splitter(text, chunk_size=120, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)
    assert all(chunk.strip() for chunk in chunks)

