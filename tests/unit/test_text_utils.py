from app.core.text_utils import chunk_text, clean_extracted_text


def test_clean_extracted_text_removes_reference_block() -> None:
    raw = "Titulo\n\nCorpo principal\n\nReferencias\nItem 1\nItem 2"
    cleaned = clean_extracted_text(raw)
    assert "Corpo principal" in cleaned
    assert "Item 1" not in cleaned


def test_chunk_text_splits_long_input() -> None:
    text = "\n\n".join([f"Paragrafo {index} com conteudo suficiente para quebrar chunk." for index in range(20)])
    chunks = chunk_text(text, max_chars=120, overlap_chars=10)
    assert len(chunks) > 1
    assert all(chunks)
