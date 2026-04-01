import pytest

from app.core.config import load_settings
from app.services.extract import DocumentExtractor

from tests.conftest import write_config_bundle


def test_extract_txt_document(tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    source = tmp_path / "sample.txt"
    source.write_text("Titulo\n\nTexto principal.", encoding="utf-8")
    extracted = DocumentExtractor(settings).extract(source)
    assert extracted.title == "Titulo"
    assert "Texto principal" in extracted.raw_text


def test_extract_docx_document(tmp_path) -> None:
    docx = pytest.importorskip("docx")
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    source = tmp_path / "sample.docx"
    document = docx.Document()
    document.add_heading("Meu Titulo", level=1)
    document.add_paragraph("Paragrafo do documento.")
    document.save(source)
    extracted = DocumentExtractor(settings).extract(source)
    assert "Paragrafo do documento." in extracted.raw_text


def test_extract_epub_document(tmp_path) -> None:
    epub = pytest.importorskip("ebooklib.epub")
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    source = tmp_path / "sample.epub"
    book = epub.EpubBook()
    book.set_identifier("id123")
    book.set_title("Livro Teste")
    chapter = epub.EpubHtml(title="Capitulo 1", file_name="chap1.xhtml", lang="pt")
    chapter.content = "<h1>Capitulo 1</h1><p>Conteudo do capitulo.</p>"
    book.add_item(chapter)
    book.spine = ["nav", chapter]
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(source), book)
    extracted = DocumentExtractor(settings).extract(source)
    assert "Conteudo do capitulo." in extracted.raw_text


def test_extract_pdf_document(tmp_path) -> None:
    fitz = pytest.importorskip("fitz")
    pytest.importorskip("pymupdf4llm")
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    source = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Titulo PDF\nTexto do PDF.")
    document.save(str(source))
    document.close()
    extracted = DocumentExtractor(settings).extract(source)
    assert "Texto do PDF" in extracted.raw_text
