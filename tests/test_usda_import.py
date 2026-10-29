import csv
import io
import zipfile

import pytest

from milo.repositories.usda import import_foundation


def make_archive(path, *, unit="G", amount="7.5", duplicate=False):
    tables = {
        "foundation_food.csv": [{"fdc_id": "123"}],
        "food.csv": [{"fdc_id": "123", "data_type": "foundation_food", "description": "Test raw food"}],
        "nutrient.csv": [
            {"id": "1003", "unit_name": unit},
            {"id": "2047", "unit_name": "KCAL"},
            {"id": "2048", "unit_name": "KCAL"},
        ],
        "food_nutrient.csv": [
            {"id": "1", "fdc_id": "123", "nutrient_id": "1003", "amount": amount},
            {"id": "2", "fdc_id": "123", "nutrient_id": "2047", "amount": "90"},
            {"id": "3", "fdc_id": "123", "nutrient_id": "2048", "amount": "88"},
            {"id": "4", "fdc_id": "999", "nutrient_id": "1003", "amount": "55"},
        ],
    }
    if duplicate:
        tables["food_nutrient.csv"].append(tables["food_nutrient.csv"][0])
    with zipfile.ZipFile(path, "w") as archive:
        for name, rows in tables.items():
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            archive.writestr("fixture/" + name, stream.getvalue())


def selection():
    return [
        {
            "fdc_id": 123,
            "expected_description": "Test raw food",
            "name_es": "Prueba cruda",
            "state": "raw",
            "allergen_review_complete": True,
        }
    ]


def test_join_uses_food_and_nutrient_ids_with_energy_precedence(tmp_path):
    path = tmp_path / "test.zip"
    make_archive(path)
    food = import_foundation(path, selection(), source_id="TEST_ONLY", source_version="1")[0]
    assert str(food.nutrients_per_100g.protein_g) == "7.5"
    assert food.nutrients_per_100g.kcal == 88
    assert food.nutrients_per_100g.fat_g is None
    assert food.nutrient_ids["kcal"] == 2048
    assert food.nutrient_record_ids["protein_g"] == 1


@pytest.mark.parametrize("amount,expected", [("", None), ("0", 0)])
def test_blank_is_null_but_reported_zero_is_zero(tmp_path, amount, expected):
    path = tmp_path / "test.zip"
    make_archive(path, amount=amount)
    food = import_foundation(path, selection(), source_id="TEST_ONLY", source_version="1")[0]
    assert food.nutrients_per_100g.protein_g == expected


@pytest.mark.parametrize("options,error", [({"unit": "MG"}, "Unidad"), ({"duplicate": True}, "duplicado")])
def test_rejects_wrong_units_and_duplicate_measurements(tmp_path, options, error):
    path = tmp_path / "test.zip"
    make_archive(path, **options)
    with pytest.raises(ValueError, match=error):
        import_foundation(path, selection(), source_id="TEST_ONLY", source_version="1")


def test_description_change_requires_review(tmp_path):
    path = tmp_path / "test.zip"
    make_archive(path)
    selected = selection()
    selected[0]["expected_description"] = "Test cooked food"
    with pytest.raises(ValueError, match="Descripción"):
        import_foundation(path, selected, source_id="TEST_ONLY", source_version="1")
