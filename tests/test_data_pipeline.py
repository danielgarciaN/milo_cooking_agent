import hashlib
import importlib
import json
import pkgutil
import zipfile
from pathlib import Path

import pytest

import milo
from milo.models import DataSource, Recipe
from milo.nutrition import calculate_recipe_nutrition, validate_recipe
from milo.usda import import_foundation, import_foundation_json

ROOT = Path(__file__).resolve().parents[1]


def test_all_package_modules_import_without_key():
    for info in pkgutil.walk_packages(milo.__path__, milo.__name__ + "."):
        importlib.import_module(info.name)


def test_catalog_coverage_and_real_ids(real_catalog):
    assert len(real_catalog.foods) >= 100
    assert len({f.fdc_id for f in real_catalog.foods.values()}) == len(real_catalog.foods)
    sources = {s["source_id"] for s in json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))}
    for food in real_catalog.foods.values():
        assert food.fdc_id and food.source_id in sources
        assert "?" not in food.name_es and "\ufffd" not in food.name_es
        assert food.review_status == "verified" and food.state != "unknown"
        assert "TEST" not in food.source_id


@pytest.mark.parametrize(
    "selection,archive,source,version,kind",
    [
        (
            "seleccion_foundation_2026_04.json",
            "FoodData_Central_foundation_food_csv_2026-04-30.zip",
            "USDA_FOUNDATION_2026_04",
            "2026-04-30",
            "foundation_food",
        ),
        (
            "seleccion_sr_legacy.json",
            "FoodData_Central_sr_legacy_food_csv_2018-04.zip",
            "USDA_SR_LEGACY_2018",
            "2018-04",
            "sr_legacy_food",
        ),
        (
            "seleccion_foundation_2026_10.json",
            "FoodData_Central_foundation_food_json_2026-10-29.zip",
            "USDA_FOUNDATION_JSON_2026_10",
            "2026-10-29",
            "json",
        ),
    ],
)
def test_catalog_values_match_official_archive(real_catalog, selection, archive, source, version, kind):
    path = ROOT / "data/usda" / archive
    if not path.exists():
        pytest.skip("Descargar fuentes para verificación contra USDA")
    chosen = json.loads((ROOT / "data/usda" / selection).read_text(encoding="utf-8"))
    fn = import_foundation_json if kind == "json" else import_foundation
    options = {} if kind == "json" else {"data_type": kind}
    regenerated = fn(path, chosen, source_id=source, source_version=version, **options)
    for food in regenerated:
        actual = real_catalog.lookup_food(food.food_id)
        if actual.source_id == source:
            assert actual == food


def test_usda_energy_and_null_reference(real_catalog):
    # SR Legacy 171413: comparación independiente de la fórmula, no macros de ejemplo.
    oil = real_catalog.lookup_food("fdc_171413")
    assert oil.nutrients_per_100g.kcal == 884
    assert oil.nutrients_per_100g.fat_g == 100
    assert oil.nutrient_ids["kcal"] == 1008
    # Foundation AOVE no publica estos nutrientes en el archivo utilizado.
    assert real_catalog.lookup_food("fdc_748608").nutrients_per_100g.kcal is None


def test_recipes_have_specific_steps_and_truthful_status(real_catalog):
    recipes = [
        Recipe.model_validate(r) for r in json.loads((ROOT / "data/recipes.json").read_text(encoding="utf-8"))
    ]
    assert len(recipes) >= 20
    assert len({r.recipe_id for r in recipes}) == len(recipes)
    for recipe in recipes:
        assert all(i.food_id in real_catalog.foods for i in recipe.ingredients)
        assert len(recipe.steps) >= 2
        assert set(recipe.tags) & {"desayuno", "comida", "cena", "snack"}
        validation = validate_recipe(recipe, real_catalog)
        assert (recipe.review_status == "verified") == validation.valid
        assert recipe.allergens == validation.allergens
        assert calculate_recipe_nutrition(recipe, real_catalog).complete


def test_source_hashes_and_format():
    for value in json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8")):
        source = DataSource.model_validate(value)
        if not source.path:
            continue
        path = ROOT / source.path
        if not path.exists():
            pytest.skip("Descargar fuentes para verificar hashes")
        with path.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == source.sha256
        assert path.stat().st_size == source.size_bytes
        if source.file_type == "zip":
            with zipfile.ZipFile(path) as archive:
                assert archive.testzip() is None


def test_incomplete_october_csv_cannot_be_imported():
    path = ROOT / "data/usda/FoodData_Central_foundation_food_csv_2026-10-29.zip"
    if not path.exists():
        pytest.skip("Descargar ZIP para comprobar incidencia")
    with pytest.raises(ValueError, match="food.csv"):
        import_foundation(path, [], source_id="TEST", source_version="2026-10-29")
