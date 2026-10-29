"""Extracción por página/sección sin red; conserva la procedencia de cada fragmento."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader

from milo.models import DataSource, DocumentChunk


def clean_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\xad", "").replace("\u0002", "")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()).strip()


def split_sections(text: str) -> list[tuple[str, str]]:
    """Heurística conservadora de títulos; conserva todo el texto y no cruza páginas."""
    sections, lines, title = [], [], "Contenido"
    for line in text.splitlines():
        is_heading = 4 <= len(line) <= 100 and (
            line.isupper() or bool(re.match(r"^\d+(?:\.\d+)*[.)]?\s+[A-ZÁÉÍÓÚÑ]", line))
        )
        if is_heading:
            if lines:
                sections.append((title, "\n".join(lines)))
            title, lines = line, [line]
        else:
            lines.append(line)
    if lines:
        sections.append((title, "\n".join(lines)))
    return sections


def chunk_page(
    text: str, *, source: DataSource, page: int, max_words: int = 350, overlap_words: int = 40
) -> list[DocumentChunk]:
    if max_words <= 0 or not 0 <= overlap_words < max_words:
        raise ValueError("Solapamiento debe ser menor que el tamaño y no negativo")
    if not source.sha256:
        raise ValueError("La fuente debe tener hash verificado")
    chunks = []
    for section_index, (title, body) in enumerate(split_sections(clean_text(text))):
        words = body.split()
        for start in range(0, len(words), max_words - overlap_words):
            content = " ".join(words[start : start + max_words])
            if not content:
                continue
            identity = f"{source.source_id}:{source.sha256}:{page}:{section_index}:{start}:{content}"
            chunks.append(
                DocumentChunk(
                    chunk_id=hashlib.sha256(identity.encode()).hexdigest(),
                    text=content,
                    source_id=source.source_id,
                    source_url=source.url,
                    source_sha256=source.sha256,
                    page=page,
                    section=title,
                    version=source.version,
                    usage=source.usage,
                )
            )
            if start + max_words >= len(words):
                break
    return chunks


def ingest_pdf(
    path: Path, source: DataSource, *, max_words: int = 350, overlap_words: int = 40
) -> tuple[list[DocumentChunk], dict]:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if source.file_type != "pdf" or source.sha256 != digest:
        raise ValueError("PDF no coincide con el registro de procedencia")
    reader = PdfReader(path)
    chunks, empty_pages = [], []
    for number, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if not text:
            empty_pages.append(number)
            continue
        chunks.extend(
            chunk_page(text, source=source, page=number, max_words=max_words, overlap_words=overlap_words)
        )
    return chunks, {
        "source_id": source.source_id,
        "pages": len(reader.pages),
        "empty_pages": empty_pages,
        "chunks": len(chunks),
        "words": sum(len(c.text.split()) for c in chunks),
        "ocr_needed": bool(empty_pages),
        "section_method": "heuristic_headings_with_page_boundaries",
    }
