"""RAG de MILO: documentos → fragmentos → Gemini Embeddings → ChromaDB → fragmentos recuperados → Gemini.

"Estos son mis tres documentos. Así los divido. Así los convierto en vectores. Aquí los guardo.
Cuando pregunto algo, estos son los fragmentos que recupera. Y esta es la respuesta que genera Gemini."
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader

from milo.config import ROOT, SOURCES_JSON, SYSTEM_PROMPT_FILE, Settings
from milo.models import DataSource, DocumentChunk

# ---------------------------------------------------------------- 1. Leer y limpiar


def load_system_prompt() -> str:
    """El system prompt vive en src/milo/prompts/system.md para poder leerlo y editarlo fácilmente."""
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


def clean_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\xad", "").replace("\u0002", "")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)  # Une palabras cortadas con guion al final de línea.
    text = re.sub(r"fi\s+(?=[a-záéíóúñ])", "fi", text)  # La ligadura "ﬁ" del PDF sale como "refi nadas".
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()).strip()


def split_sections(text: str) -> list[tuple[str, str]]:
    """Separo por títulos: '## ...' en Markdown o líneas en MAYÚSCULAS en el PDF."""
    sections, lines, title = [], [], "Contenido"
    for line in text.splitlines():
        heading = line.startswith("## ") or (4 <= len(line) <= 100 and line.isupper())
        if heading:
            if lines:
                sections.append((title, "\n".join(lines)))
            title, lines = line.lstrip("# "), [line]
        else:
            lines.append(line)
    if lines:
        sections.append((title, "\n".join(lines)))
    return sections


# ---------------------------------------------------------------- 2. Chunking


def chunk_page(
    text: str,
    *,
    source: DataSource,
    page: int | None,
    max_words: int = 400,
    overlap_words: int = 50,
    merge_short: bool = False,
) -> list[DocumentChunk]:
    """Divido un texto en fragmentos de hasta 400 palabras, con 50 de solapamiento si una sección es larga."""
    if max_words <= 0 or not 0 <= overlap_words < max_words:
        raise ValueError("Solapamiento debe ser menor que el tamaño y no negativo")
    if not source.sha256:
        raise ValueError("La fuente debe tener hash verificado")
    sections = split_sections(clean_text(text))
    if merge_short:
        # En un PDF, un título en varias líneas no debe producir fragmentos de dos palabras.
        grouped = []
        for title, body in sections:
            if grouped and len(grouped[-1][1].split()) < 100:
                previous_title, previous_body = grouped.pop()
                grouped.append((previous_title, previous_body + "\n" + body))
            else:
                grouped.append((title, body))
        sections = grouped
    chunks = []
    for section_index, (title, body) in enumerate(sections):
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


def check_source(path: Path, source: DataSource) -> None:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if source.sha256 != digest:
        raise ValueError(
            f"El documento {source.source_id} ha cambiado y no coincide con sources.json. "
            "Si lo he editado a propósito, ejecuto python scripts/prepare_recipes.py para registrar el nuevo hash."
        )


def ingest_pdf(
    path: Path, source: DataSource, *, max_words: int = 400, overlap_words: int = 50
) -> tuple[list[DocumentChunk], dict]:
    check_source(path, source)
    reader = PdfReader(path)
    chunks, empty_pages = [], []
    for number, page in enumerate(reader.pages, start=1):
        if number in source.skip_pages:
            continue
        text = clean_text(page.extract_text() or "")
        if not text:
            empty_pages.append(number)
            continue
        chunks.extend(
            chunk_page(
                text,
                source=source,
                page=number,
                max_words=max_words,
                overlap_words=overlap_words,
                merge_short=True,
            )
        )
    return chunks, {
        "source_id": source.source_id,
        "pages": len(reader.pages),
        "skipped_pages": source.skip_pages,
        "empty_pages": empty_pages,
        "chunks": len(chunks),
    }


def rag_sources(root: Path = ROOT) -> list[DataSource]:
    """Las fuentes marcadas como rag_general en data/sources.json: mis tres documentos."""
    sources = [DataSource.model_validate(s) for s in json.loads(SOURCES_JSON.read_text(encoding="utf-8"))]
    return [s for s in sources if s.usage == "rag_general" and s.path and (root / s.path).exists()]


def load_documents(root: Path = ROOT) -> list[DocumentChunk]:
    """Leo los PDF/Markdown reales y devuelvo todos sus fragmentos con metadatos de procedencia."""
    chunks = []
    for source in rag_sources(root):
        path = root / source.path
        check_source(path, source)
        if source.file_type == "pdf":
            pages, report = ingest_pdf(path, source)
            if report["empty_pages"]:
                raise ValueError(f"Revisar páginas sin texto de {source.source_id}: {report['empty_pages']}")
            chunks.extend(pages)
        elif source.file_type == "markdown":
            chunks.extend(chunk_page(path.read_text(encoding="utf-8"), source=source, page=None))
    if not chunks:
        raise ValueError("No hay documentos de conocimiento disponibles en data/documents")
    return chunks


# ---------------------------------------------------------------- 3. Embeddings y modelo Gemini


def create_embeddings(settings: Settings):
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.require_key(),
        output_dimensionality=settings.embedding_dimension,
    )


@lru_cache(maxsize=1)
def generation_limiter():
    from langchain_core.rate_limiters import InMemoryRateLimiter

    # Como máximo 15 llamadas por minuto, el límite habitual de la capa gratuita de Gemini.
    return InMemoryRateLimiter(requests_per_second=0.25, check_every_n_seconds=0.1, max_bucket_size=2)


def create_model(settings: Settings, tools: list | None = None):
    """Gemini como LLM. Con `tools`, el modelo puede pedir que se ejecuten herramientas Python."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    def build(name: str):
        model = ChatGoogleGenerativeAI(
            model=name,
            google_api_key=settings.require_key(),
            max_output_tokens=2048,
            max_retries=3,
            timeout=60,
            rate_limiter=generation_limiter(),
        )
        return model.bind_tools(tools) if tools else model

    primary = build(settings.model)
    if settings.fallback_model and settings.fallback_model != settings.model:
        return primary.with_fallbacks([build(settings.fallback_model)])
    return primary


# ---------------------------------------------------------------- 4. ChromaDB


def collection_name(chunks: list[DocumentChunk], settings: Settings) -> str:
    """El nombre depende de los fragmentos y del modelo: si cambian, se crea una colección nueva."""
    identity = json.dumps(
        {
            "model": settings.embedding_model,
            "dimension": settings.embedding_dimension,
            "chunks": sorted(c.chunk_id for c in chunks),
        },
        sort_keys=True,
    )
    return "milo_" + hashlib.sha256(identity.encode()).hexdigest()[:16]


def open_index(chunks: list[DocumentChunk], settings: Settings):
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=collection_name(chunks, settings),
        embedding_function=create_embeddings(settings),
        persist_directory=str(settings.storage_dir / "chroma"),
        collection_metadata={"hnsw:space": "cosine"},
    )


def index_chunks(chunks: list[DocumentChunk], settings: Settings):
    """Creo solo los vectores que faltan. Repetir la indexación no duplica el corpus."""
    if not chunks:
        raise ValueError("Corpus vacío")
    from langchain_core.documents import Document

    store = open_index(chunks, settings)
    existing = set(store.get()["ids"])
    new = [c for c in chunks if c.chunk_id not in existing]
    for start in range(0, len(new), 16):
        batch = new[start : start + 16]
        documents = [
            Document(
                page_content=c.text,
                metadata={
                    k: v for k, v in c.model_dump().items() if k not in {"text", "chunk_id"} and v is not None
                },
            )
            for c in batch
        ]
        store.add_documents(documents, ids=[c.chunk_id for c in batch])
    return store


# ---------------------------------------------------------------- 5. Recuperar y generar


def message_text(message) -> str:
    if isinstance(message.content, str):
        return message.content
    return "\n".join(
        block.get("text", "")
        for block in message.content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def cited_numbers(text: str) -> set[int]:
    """Números citados en la respuesta: admite [1], [1, 2] y [1][3]."""
    return {int(n) for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", text) for n in group.split(",")}


def format_context(fragments: list[dict]) -> str:
    return "\n\n".join(
        f"[{f['citation']}] {f['metadata']['source_id']} — {location(f['metadata'])}\n{f['text']}"
        for f in fragments
    )


def location(meta: dict) -> str:
    return f"página {meta['page']}" if meta.get("page") else meta.get("section", "")


@dataclass
class RagAnswer:
    question: str
    fragments: list[dict]
    answer: str

    @property
    def cited(self) -> set[int]:
        return cited_numbers(self.answer) & {f["citation"] for f in self.fragments}


class NutritionRAG:
    """El notebook, el agente LangGraph y la app de Streamlit comparten este mismo RAG."""

    def __init__(self, settings: Settings | None = None, *, build_if_missing: bool = True):
        self.settings = settings or Settings()
        self.chunks = load_documents()
        self.store = open_index(self.chunks, self.settings)
        if set(self.store.get()["ids"]) != {c.chunk_id for c in self.chunks}:
            if not build_if_missing:
                raise RuntimeError("Falta indexar el corpus actual. Ejecuta python scripts/build_index.py")
            # Primera ejecución (por ejemplo en Streamlit Cloud): genero los embeddings que falten.
            self.store = index_chunks(self.chunks, self.settings)
        self.model = create_model(self.settings)
        self.system_prompt = load_system_prompt()

    def retrieve(self, question: str, k: int = 4) -> list[dict]:
        """Busco en Chroma los k fragmentos más parecidos (distancia coseno: menor = más parecido)."""
        if not question.strip() or not 1 <= k <= 10:
            raise ValueError("Pregunta vacía o número de fragmentos fuera de 1–10")
        results = self.store.similarity_search_with_score(question, k=k)
        return [
            {"citation": i, "text": doc.page_content, "metadata": doc.metadata, "distance": float(score)}
            for i, (doc, score) in enumerate(results, start=1)
        ]

    def generate(self, question: str, fragments: list[dict]) -> str:
        """Gemini responde usando el system prompt de MILO y los fragmentos recuperados como contexto."""
        if not fragments:
            return "No he recuperado información suficiente en mis documentos para responder."
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=f"<documentos>\n{format_context(fragments)}\n</documentos>\n\nPregunta: {question}"
            ),
        ]
        text = message_text(self.model.invoke(messages)).strip()
        if text and not cited_numbers(text) & {f["citation"] for f in fragments}:
            # Compruebo las citas: si no hay ninguna válida, pido una vez que reescriba la respuesta citando.
            messages += [
                AIMessage(content=text),
                HumanMessage(
                    content="Reescribe tu respuesta citando con [n] los fragmentos en los que te basas."
                ),
            ]
            text = message_text(self.model.invoke(messages)).strip() or text
        if not text:
            raise ValueError("Gemini ha devuelto una respuesta vacía")
        return text

    def ask(self, question: str, k: int = 4) -> RagAnswer:
        fragments = self.retrieve(question, k=k)
        return RagAnswer(question, fragments, self.generate(question, fragments))


def show_answer(result: RagAnswer, *, label: str = "RESPUESTA DE GEMINI", width: int = 300) -> None:
    print(f"PREGUNTA: {result.question}\n")
    print("FRAGMENTOS RECUPERADOS DE CHROMADB:")
    for fragment in result.fragments:
        meta = fragment["metadata"]
        mark = "★" if fragment["citation"] in result.cited else " "
        distance = f" · distancia {fragment['distance']:.3f}" if "distance" in fragment else ""
        print(f"{mark}[{fragment['citation']}] {meta['source_id']} — {location(meta)}{distance}")
        print(
            "    "
            + fragment["text"][:width].replace("\n", " ")
            + ("…" if len(fragment["text"]) > width else "")
        )
    print(f"\n{label}:\n{result.answer}")
    print("\n★ = fragmento citado en la respuesta")
