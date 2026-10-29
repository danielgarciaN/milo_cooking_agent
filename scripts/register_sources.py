"""Actualiza fuentes desde evidencia de descarga, sin heredar estados del borrador."""

import json
from pathlib import Path

from download_sources import SOURCES, inspect_file

from milo.models import DataSource

ROOT = Path(__file__).resolve().parents[1]
TITLES = {
    "AESAN_2022": "Recomendaciones dietéticas saludables y sostenibles (AESAN)",
    "USDA_FIELDS": "FoodData Central Download Field Descriptions",
    "USDA_FOUNDATION_2026_10": "Foundation Foods CSV octubre 2026 (incompleto)",
    "USDA_FOUNDATION_2026_04": "Foundation Foods CSV abril 2026",
    "USDA_FOUNDATION_JSON_2026_10": "Foundation Foods JSON octubre 2026",
    "USDA_SR_LEGACY_2018": "USDA SR Legacy abril 2018",
}


def main():
    manifest = json.loads((ROOT / "data/download_manifest.json").read_text(encoding="utf-8"))
    sources = []
    for sid, url, version, terms in SOURCES:
        matches = [r for r in manifest if r["url"] == url and r["status"] in {"downloaded", "provided_local"}]
        if not matches:
            sources.append(
                DataSource(
                    source_id=sid,
                    title=sid,
                    url=url,
                    version=version,
                    file_type="pdf" if url.endswith("pdf") else "zip",
                    status="failed",
                    usage_conditions=terms,
                    usage="unavailable",
                ).model_dump()
            )
            continue
        record = matches[-1]
        details = inspect_file(ROOT / record["path"])
        if details["sha256"] != record["sha256"]:
            raise ValueError(f"Hash cambió: {sid}")
        usage = (
            "rag_general"
            if sid == "AESAN_2022"
            else "data_dictionary"
            if sid == "USDA_FIELDS"
            else "structured_food_macros"
        )
        status = "incomplete_archive" if details.get("missing_usda_tables") else record["status"]
        sources.append(
            DataSource(
                source_id=sid,
                title=TITLES[sid],
                url=url,
                version=version,
                file_type=details["file_type"],
                status=status,
                downloaded_at=record.get("downloaded_at"),
                size_bytes=details["size_bytes"],
                sha256=details["sha256"],
                path=record["path"],
                usage_conditions=terms,
                usage=usage,
            ).model_dump()
        )
    original = json.loads((ROOT / "docs/materials/sources_ORIGINAL.json").read_text(encoding="utf-8"))
    for old in original:
        if old["type"] == "web":
            sources.append(
                DataSource(
                    source_id=old["id"],
                    title=old["title"],
                    url=old["url"],
                    file_type="web",
                    status="pending",
                    usage_conditions=old["license"],
                    usage=old["usage"],
                ).model_dump()
            )
    (ROOT / "data/sources.json").write_text(
        json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Fuentes registradas:", len(sources))


if __name__ == "__main__":
    main()
