"""Construyo la base de conocimiento vectorial: documentos → fragmentos → Gemini Embeddings → ChromaDB.

python scripts/build_index.py            # añade solo los fragmentos que falten
python scripts/build_index.py --rebuild  # borra storage/chroma y lo crea de cero
python scripts/build_index.py --dry-run  # solo muestra los fragmentos, sin llamar a Gemini
"""

import argparse
import shutil
from collections import Counter

from milo.config import Settings
from milo.rag import index_chunks, load_documents


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--rebuild", action="store_true", help="Borra el índice anterior antes de crearlo")
    parser.add_argument("--dry-run", action="store_true", help="No genera embeddings")
    args = parser.parse_args()
    settings = Settings()
    chunks = load_documents()
    for source, count in Counter(c.source_id for c in chunks).items():
        print(f"{source:15} {count:3} fragmentos")
    print(f"{'Total':15} {len(chunks):3} fragmentos")
    if args.dry_run:
        return
    if args.rebuild:
        shutil.rmtree(settings.storage_dir / "chroma", ignore_errors=True)
    store = index_chunks(chunks, settings)
    print(f"Vectores guardados en {settings.storage_dir / 'chroma'}: {len(store.get()['ids'])}")


if __name__ == "__main__":
    main()
