"""Leo documentos y, con --index, creo vectores reales de Gemini en Chroma."""

import argparse
from collections import Counter

from milo.config import Settings
from milo.rag import index_chunks, load_documents


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", action="store_true")
    args = parser.parse_args()
    chunks = load_documents()
    for source, count in Counter(c.source_id for c in chunks).items():
        print(source, count, "fragmentos")
    print("Total:", len(chunks))
    if args.index:
        store = index_chunks(chunks, Settings())
        print("Vectores guardados en Chroma:", len(store.get()["ids"]))


if __name__ == "__main__":
    main()
