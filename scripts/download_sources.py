"""Descarga verificable; registra fallos sin sustituirlos por éxitos simulados."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pypdf import PdfReader
from pypdf.errors import PdfReadError

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    (
        "AESAN_2022",
        "https://www.aesan.gob.es/AECOSAN/docs/documentos/nutricion/RECOMENDACIONES_DIETETICAS.pdf",
        "2022-12",
        "Revisar reutilización; incluye imágenes de terceros.",
    ),
    (
        "USDA_FOUNDATION_2026_10",
        "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2026-10-29.zip",
        "2026-10-29",
        "Datos FDC: dominio público/CC0 según https://fdc.nal.usda.gov/api-guide/",
    ),
    (
        "USDA_FIELDS",
        "https://fdc.nal.usda.gov/docs/Download_Field_Descriptions_Oct2020.pdf",
        "2020-10",
        "Documento técnico USDA; revisar componentes antes de redistribuir.",
    ),
    (
        "USDA_FOUNDATION_2026_04",
        "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2026-04-30.zip",
        "2026-04-30",
        "Datos FDC: dominio público/CC0; https://fdc.nal.usda.gov/api-guide/",
    ),
    (
        "USDA_FOUNDATION_JSON_2026_10",
        "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_json_2026-10-29.zip",
        "2026-10-29",
        "Datos FDC: dominio público/CC0; https://fdc.nal.usda.gov/api-guide/",
    ),
    (
        "USDA_SR_LEGACY_2018",
        "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip",
        "2018-04",
        "Datos FDC: dominio público/CC0; https://fdc.nal.usda.gov/api-guide/",
    ),
]


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
    parser.add_argument("--fallback-dir", type=Path)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "data/download_manifest.json"
    records = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    for source_id, url, version, terms in SOURCES:
        path = raw / url.rsplit("/", 1)[-1]
        if args.skip_existing and path.exists():
            print(source_id, "existing_file_inspected", inspect_file(path).get("size_bytes"), flush=True)
            continue
        record = {
            "source_id": source_id,
            "url": url,
            "version": version,
            "usage_conditions": terms,
            "attempted_at": datetime.now(UTC).isoformat(),
            "path": path.relative_to(ROOT).as_posix(),
            "status": "failed",
            "downloaded_at": None,
            "http_status": None,
        }
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=45) as response:
                record["http_status"] = response.status_code
                record["resolved_url"] = str(response.url)
                response.raise_for_status()
                temporary = path.with_suffix(path.suffix + ".part")
                with temporary.open("wb") as output:
                    for block in response.iter_bytes():
                        output.write(block)
            temporary.replace(path)
            record.update(
                inspect_file(path), status="downloaded", downloaded_at=datetime.now(UTC).isoformat()
            )
        except (httpx.HTTPError, OSError, ValueError, zipfile.BadZipFile, PdfReadError) as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            fallback = args.fallback_dir / path.name if args.fallback_dir else None
            if fallback and fallback.is_file():
                shutil.copy2(fallback, path)
                try:
                    record.update(
                        inspect_file(path), status="provided_local", imported_at=datetime.now(UTC).isoformat()
                    )
                except (OSError, ValueError, zipfile.BadZipFile, PdfReadError) as invalid:
                    record["validation_error"] = str(invalid)
        records.append(record)
        manifest_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            source_id,
            record["status"],
            record.get("size_bytes"),
            record.get("missing_usda_tables", ""),
            flush=True,
        )


if __name__ == "__main__":
    main()
