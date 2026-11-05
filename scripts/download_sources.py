"""Descarga verificable; registra fallos sin sustituirlos por éxitos simulados."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pypdf import PdfReader
from pypdf.errors import PdfReadError

ROOT = Path(__file__).resolve().parents[1]


def inspect_file(path: Path) -> dict:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    details = {"size_bytes": path.stat().st_size, "sha256": digest}
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        details.update(file_type="pdf", pages=len(reader.pages))
        if not reader.pages:
            raise ValueError("PDF sin páginas")
    elif path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"CRC incorrecto: {bad}")
            names = {Path(n).name for n in archive.namelist()}
            details.update(file_type="zip", members=archive.namelist())
            if "_csv_" in path.name:
                type_table = "sr_legacy_food.csv" if "sr_legacy" in path.name else "foundation_food.csv"
                details["missing_usda_tables"] = sorted(
                    {"food.csv", "food_nutrient.csv", "nutrient.csv", type_table} - names
                )
    else:
        raise ValueError("Tipo no admitido")
    return details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-existing", action="store_true", help="Compatibilidad: siempre verifico los existentes"
    )
    args = parser.parse_args()
    del args
    registry = ROOT / "data/sources.json"
    sources = json.loads(registry.read_text(encoding="utf-8"))
    for source in sources:
        if source["file_type"] not in {"pdf", "zip"} or source["usage"] == "unavailable":
            continue
        path = ROOT / (source["path"] or "data/usda/" + source["url"].rsplit("/", 1)[-1])
        if path.exists():
            details = inspect_file(path)
            if source["sha256"] and details["sha256"] != source["sha256"]:
                raise ValueError(f"Hash inesperado: {source['source_id']}")
            print(source["source_id"], "archivo existente verificado", flush=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        # Valido en una carpeta temporal antes de publicar el archivo final.
        temporary_dir = ROOT / "storage/downloads"
        temporary_dir.mkdir(parents=True, exist_ok=True)
        temporary = temporary_dir / path.name
        record = {"url": source["url"], "attempted_at": datetime.now(UTC).isoformat(), "status": "failed"}
        try:
            with httpx.stream("GET", source["url"], follow_redirects=True, timeout=45) as response:
                record["http_status"] = response.status_code
                response.raise_for_status()
                with temporary.open("wb") as output:
                    for block in response.iter_bytes():
                        output.write(block)
            details = inspect_file(temporary)
            if source["sha256"] and details["sha256"] != source["sha256"]:
                raise ValueError("La descarga no coincide con el hash registrado; revisar versión")
            temporary.replace(path)
            status = "incomplete_archive" if details.get("missing_usda_tables") else "downloaded"
            record.update(details, status=status)
            source.update({key: details[key] for key in ["size_bytes", "sha256"]})
            source.update(
                path=path.relative_to(ROOT).as_posix(),
                status=status,
                downloaded_at=datetime.now(UTC).isoformat(),
            )
        except (httpx.HTTPError, OSError, ValueError, zipfile.BadZipFile, PdfReadError) as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            source["status"] = "failed"
        source.setdefault("download_attempts", []).append(record)
        registry.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
        print(source["source_id"], record["status"], flush=True)


if __name__ == "__main__":
    main()
