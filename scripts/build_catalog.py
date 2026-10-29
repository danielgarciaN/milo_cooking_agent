"""Regenera el CSV exclusivamente desde IDs revisados y las tablas oficiales."""

import json
from pathlib import Path

from milo.repositories.catalog import FoodCatalog
from milo.repositories.usda import import_foundation, import_foundation_json, write_food_csv

ROOT = Path(__file__).resolve().parents[1]


def main():
    selection = json.loads((ROOT / "data/structured/food_selection.json").read_text(encoding="utf-8"))
    foods = import_foundation(
        ROOT / "data/raw/FoodData_Central_foundation_food_csv_2026-04-30.zip",
        selection,
        source_id="USDA_FOUNDATION_2026_04",
        source_version="2026-04-30",
    )
    october = json.loads((ROOT / "data/structured/food_selection_october.json").read_text(encoding="utf-8"))
    upgrades = import_foundation_json(
        ROOT / "data/raw/FoodData_Central_foundation_food_json_2026-10-29.zip",
        october,
        source_id="USDA_FOUNDATION_JSON_2026_10",
        source_version="2026-10-29",
    )
    by_id = {f.food_id: f for f in foods}
    by_id.update({f.food_id: f for f in upgrades})
    foods = list(by_id.values())
    extra = json.loads((ROOT / "data/structured/food_selection_sr.json").read_text(encoding="utf-8"))
    foods.extend(
        import_foundation(
            ROOT / "data/raw/FoodData_Central_sr_legacy_food_csv_2018-04.zip",
            extra,
            source_id="USDA_SR_LEGACY_2018",
            source_version="2018-04",
            data_type="sr_legacy_food",
        )
    )
    output = ROOT / "data/structured/foods.csv"
    write_food_csv(foods, output)
    reloaded = FoodCatalog.from_csv(output)
    assert len(reloaded.foods) == len(foods)
    report = {
        "sources": sorted({f.source_id for f in foods}),
        "food_count": len(foods),
        "foundation_count": sum(f.source_id != "USDA_SR_LEGACY_2018" for f in foods),
        "complete_macros_count": sum(
            all(
                getattr(f.nutrients_per_100g, k) is not None
                for k in ["kcal", "protein_g", "carbs_g", "fat_g"]
            )
            for f in foods
        ),
        "missing_nutrients": {
            f.food_id: [k for k, v in f.nutrients_per_100g.model_dump().items() if v is None]
            for f in foods
            if None in f.nutrients_per_100g.model_dump().values()
        },
        "coverage_gaps": ["Composición y trazas de marcas comerciales concretas"],
        "supplement_note": "SR Legacy añade aceite de oliva genérico, girasol linoleico, tofu firme con calcio, quinoa seca y lentejas cocidas; no equivalencias con otros FDC IDs.",
        "energy_precedence": [2048, 2047, 1008],
        "validation_scope": "Esquema, identidad FDC, tablas, unidades y valores de fuente; no análisis de laboratorio propio.",
    }
    (ROOT / "evaluation/catalog_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
