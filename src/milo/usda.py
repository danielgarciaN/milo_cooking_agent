"""Importador de las tablas oficiales Foundation Foods; sin estimaciones de nutrientes."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from decimal import Decimal
from pathlib import Path

from milo.models import Food, NutrientValues

NUTRIENT_IDS = {
    "protein_g": [1003],
    "carbs_g": [1005],
    "fat_g": [1004],
    "fiber_g": [1079],
    "kcal": [2048, 2047, 1008],
}


def read_table(archive: zipfile.ZipFile, filename: str) -> list[dict[str, str]]:
    candidates = [n for n in archive.namelist() if Path(n).name == filename]
    if len(candidates) != 1:
        raise ValueError(f"Se requiere una tabla {filename}; encontradas: {len(candidates)}")
    with archive.open(candidates[0]) as raw:
        return list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig")))


def import_foundation(
    archive_path: Path,
    selection: list[dict],
    *,
    source_id: str,
    source_version: str,
    data_type: str = "foundation_food",
) -> list[Food]:
    if data_type not in {"foundation_food", "sr_legacy_food"}:
        raise ValueError("Tipo USDA no soportado")
    with zipfile.ZipFile(archive_path) as archive:
        foundations = {int(r["fdc_id"]) for r in read_table(archive, data_type + ".csv")}
        foods = {int(r["fdc_id"]): r for r in read_table(archive, "food.csv")}
        nutrients = {int(r["id"]): r for r in read_table(archive, "nutrient.csv")}
        wanted = {r["fdc_id"] for r in selection}
        values: dict[int, dict[int, dict]] = {}
        for row in read_table(archive, "food_nutrient.csv"):
            fdc_id, nutrient_id = int(row["fdc_id"]), int(row["nutrient_id"])
            if fdc_id not in wanted:
                continue
            bucket = values.setdefault(fdc_id, {})
            if nutrient_id in bucket:
                raise ValueError(f"Nutriente duplicado: {fdc_id}/{nutrient_id}")
            bucket[nutrient_id] = row
    result = []
    for selected in selection:
        fdc_id = selected["fdc_id"]
        if fdc_id not in foundations or fdc_id not in foods:
            raise ValueError(f"FDC ID no es {data_type}: {fdc_id}")
        source_food = foods[fdc_id]
        if source_food["data_type"] != data_type:
            raise ValueError(f"Tipo incorrecto: {fdc_id}")
        if selected["expected_description"] != source_food["description"]:
            raise ValueError(f"Descripción cambió: revisar selección {fdc_id}")
        amounts, chosen_ids, record_ids = {}, {}, {}
        for name, candidates in NUTRIENT_IDS.items():
            amounts[name] = None
            for nutrient_id in candidates:
                row = values.get(fdc_id, {}).get(nutrient_id)
                if not row or not row["amount"].strip():
                    continue
                expected_unit = "KCAL" if name == "kcal" else "G"
                if nutrients[nutrient_id]["unit_name"].upper() != expected_unit:
                    raise ValueError(f"Unidad incompatible: {fdc_id}/{nutrient_id}")
                amounts[name] = Decimal(row["amount"])
                chosen_ids[name] = nutrient_id
                record_ids[name] = int(row["id"])
                break
        meta = {k: v for k, v in selected.items() if k not in {"fdc_id", "expected_description"}}
        result.append(
            Food(
                food_id=f"fdc_{fdc_id}",
                fdc_id=fdc_id,
                name_source=source_food["description"],
                nutrients_per_100g=NutrientValues(**amounts),
                source_id=source_id,
                source_version=source_version,
                review_status="verified",
                nutrient_ids=chosen_ids,
                nutrient_record_ids=record_ids,
                **meta,
            )
        )
    return result


def write_food_csv(foods: list[Food], output: Path) -> None:
    rows = []
    for food in foods:
        row = food.model_dump(mode="json")
        nutrients = row.pop("nutrients_per_100g")
        row.update({key + "_100g": value for key, value in nutrients.items()})
        for key in [
            "allergens",
            "nutrient_ids",
            "nutrient_record_ids",
            "allergen_review_complete",
            "is_compound",
            "vegan",
            "vegetarian",
        ]:
            value = sorted(row[key]) if key == "allergens" else row[key]
            row[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        rows.append(row)
    if not rows:
        raise ValueError("No se exporta un catálogo vacío")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def import_foundation_json(
    archive_path: Path, selection: list[dict], *, source_id: str, source_version: str
) -> list[Food]:
    """Registros completos de otra edición; jamás mezcla nutrientes entre FDC IDs."""
    with zipfile.ZipFile(archive_path) as archive:
        names = [n for n in archive.namelist() if n.endswith(".json")]
        if len(names) != 1:
            raise ValueError("Se requiere un único JSON USDA")
        originals = {f["fdcId"]: f for f in json.loads(archive.read(names[0]))["FoundationFoods"]}
    result = []
    for selected in selection:
        fid = selected["fdc_id"]
        original = originals[fid]
        if original["description"] != selected["expected_description"]:
            raise ValueError(f"Descripción cambió: {fid}")
        values = {}
        for n in original["foodNutrients"]:
            nid = n["nutrient"]["id"]
            if nid in values:
                raise ValueError(f"Nutriente duplicado: {fid}/{nid}")
            values[nid] = n
        amounts, chosen, records = {}, {}, {}
        for key, candidates in NUTRIENT_IDS.items():
            amounts[key] = None
            for nid in candidates:
                n = values.get(nid)
                if not n or n.get("amount") is None:
                    continue
                expected = "KCAL" if key == "kcal" else "G"
                if n["nutrient"]["unitName"].upper() != expected:
                    raise ValueError(f"Unidad incompatible: {fid}/{nid}")
                amounts[key] = Decimal(str(n["amount"]))
                chosen[key], records[key] = nid, n["id"]
                break
        meta = {k: v for k, v in selected.items() if k not in {"fdc_id", "expected_description"}}
        result.append(
            Food(
                food_id=f"fdc_{fid}",
                fdc_id=fid,
                name_source=original["description"],
                nutrients_per_100g=NutrientValues(**amounts),
                nutrient_ids=chosen,
                nutrient_record_ids=records,
                source_id=source_id,
                source_version=source_version,
                review_status="verified",
                **meta,
            )
        )
    return result
