"""Adaptador opcional: solo se conecta a Gemini cuando se invoca explícitamente."""

import hashlib
import json

from milo.config import Settings
from milo.models import DocumentChunk
from milo.rag.embeddings import create_embeddings


def index_chunks(chunks: list[DocumentChunk], settings: Settings):
    if not chunks:
        raise ValueError("Corpus vacío")
    embeddings = create_embeddings(settings)
    from langchain_chroma import Chroma
    from langchain_core.documents import Document

    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "model": settings.embedding_model,
                "dimension": settings.embedding_dimension,
                "chunks": sorted(c.chunk_id for c in chunks),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()[:20]
    store = Chroma(
        collection_name=f"milo_{fingerprint}",
        embedding_function=embeddings,
        persist_directory=str(settings.storage_dir / "chroma"),
    )
    existing = set(store.get()["ids"])
    new = [c for c in chunks if c.chunk_id not in existing]
    for offset in range(0, len(new), 32):
        batch = new[offset : offset + 32]
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
