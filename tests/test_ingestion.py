import json
from pathlib import Path

import pytest

from milo.config import Settings
from milo.models import DataSource
from milo.rag import chunk_page, clean_text, create_embeddings, ingest_pdf

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def source():
    return DataSource(
        source_id="test",
        title="Test",
        url="https://example.org/test.pdf",
        file_type="pdf",
        status="pending",
        usage_conditions="Test only",
        usage="test",
        sha256="a" * 64,
    )


def test_clean_and_section_provenance(source):
    chunks = chunk_page("TÍTULO UNO\nTexto de prue-\nba.\nTÍTULO DOS\nMás texto.", source=source, page=3)
    assert len(chunks) == 2
    assert "prueba" in chunks[0].text
    assert all(c.page == 3 and c.source_sha256 == "a" * 64 for c in chunks)
    assert chunks[0].section == "TÍTULO UNO"
    assert clean_text(" a\x00  b\n c ") == "a b\nc"


def test_stable_ids_and_word_bounds(source):
    text = " ".join(f"palabra{i}" for i in range(31))
    a = chunk_page(text, source=source, page=1, max_words=10, overlap_words=2)
    b = chunk_page(text, source=source, page=1, max_words=10, overlap_words=2)
    assert a == b
    assert all(len(c.text.split()) <= 10 for c in a)
    assert set(text.split()) == {word for c in a for word in c.text.split()}
    assert len({c.chunk_id for c in a}) == len(a)


def test_bad_overlap(source):
    with pytest.raises(ValueError):
        chunk_page("contenido", source=source, page=1, max_words=10, overlap_words=10)


def test_pdf_ingestion_actual_aesan():
    raw = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))
    source = DataSource.model_validate(next(s for s in raw if s["source_id"] == "AESAN_2022"))
    path = ROOT / source.path
    if not path.exists():
        pytest.skip("Descargar AESAN para la prueba real")
    chunks, report = ingest_pdf(path, source)
    assert report["pages"] == 19
    assert not report["empty_pages"]
    assert "legumbres" in " ".join(c.text.lower() for c in chunks)
    # Portada, índice y contraportada (páginas 1, 2 y 19) no se indexan.
    assert {c.page for c in chunks} == set(range(3, 19))
    assert report["skipped_pages"] == [1, 2, 19]
    source.sha256 = "0" * 64
    with pytest.raises(ValueError, match="sources.json"):
        ingest_pdf(path, source)


def test_missing_key_fails_without_network(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Falta"):
        create_embeddings(Settings(_env_file=None))
