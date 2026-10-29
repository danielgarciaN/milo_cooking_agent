"""Prepara JSONL offline. --index activa explícitamente Gemini + Chroma."""

import argparse
import json
from pathlib import Path

from milo.config import Settings
from milo.models import DataSource
from milo.rag.ingestion import ingest_pdf

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", action="store_true")
    parser.add_argument("--query", default="¿Qué recomienda la guía sobre las legumbres?")
    args = parser.parse_args()
    sources = [
        DataSource.model_validate(s)
        for s in json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))
    ]
    reports, domain_chunks = [], []
    processed = ROOT / "data/processed"
    processed.mkdir(parents=True, exist_ok=True)
    for source in sources:
        if source.file_type != "pdf" or source.status not in {"downloaded", "provided_local"}:
            continue
        chunks, report = ingest_pdf(ROOT / source.path, source)
        (processed / f"{source.source_id}.jsonl").write_text(
            "\n".join(c.model_dump_json() for c in chunks) + "\n", encoding="utf-8"
        )
        reports.append(report)
        if source.usage == "rag_general":
            domain_chunks.extend(chunks)
    summary = {
        "sources": reports,
        "domain_chunks": len(domain_chunks),
        "academic_corpus_ready": False,
        "reason": "AESAN es una guía de 19 páginas; el diccionario USDA no sustituye conocimiento culinario. Ampliar corpus y revisar reutilización.",
        "embeddings_executed": False,
    }
    (ROOT / "evaluation/ingestion_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.index:
        from milo.rag.retrieval import index_chunks

        store = index_chunks(domain_chunks, Settings())
        results = store.similarity_search_with_score(args.query, k=4)
        live = {
            "query": args.query,
            "results": [
                {"text": d.page_content, "metadata": d.metadata, "distance": score} for d, score in results
            ],
        }
        (ROOT / "evaluation/results/retrieval_live.json").write_text(
            json.dumps(live, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("Indexación y consulta completadas; ver evaluation/results/retrieval_live.json")


if __name__ == "__main__":
    main()
