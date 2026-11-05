from decimal import Decimal

import pytest
from pydantic import ValidationError

from milo.models import NutrientValues, RecipeIngredient
from milo.nutrition import calculate_nutrition, calculate_recipe_nutrition


@pytest.mark.parametrize("grams,expected", [(100, 100), (150, 150), (250, 250)])
def test_scale_100_150_250(catalog, grams, expected):
    item = RecipeIngredient(ingredient_name="A", food_id="a", grams=grams, state="raw")
    result = calculate_nutrition([item], catalog)
    assert result.totals.kcal == expected
    assert result.totals.protein_g == Decimal(expected) / 10
    assert result.complete and result.approximate


def test_sum_and_servings(catalog, recipe):
    result = calculate_recipe_nutrition(recipe, catalog)
    assert result.totals == NutrientValues(
        kcal=200, protein_g=20, carbs_g=Decimal("27.5"), fat_g=4, fiber_g=6
    )
    assert result.per_serving.kcal == 100
    assert result.per_serving.carbs_g == Decimal("13.75")


def test_missing_propagates_without_inventing_zero(catalog, recipe):
    catalog.foods["b"].nutrients_per_100g.protein_g = None
    result = calculate_recipe_nutrition(recipe, catalog)
    assert result.totals.protein_g is None and result.per_serving.protein_g is None
    assert result.totals.kcal == 200
    assert not result.complete
    assert "protein_g" in result.missing["1:B"]


def test_missing_fiber_does_not_block_complete_macros(catalog, recipe):
    catalog.foods["a"].nutrients_per_100g.fiber_g = None
    result = calculate_recipe_nutrition(recipe, catalog)
    assert result.complete
    assert result.totals.fiber_g is None
    assert result.missing == {"0:A": ["fiber_g"]}


@pytest.mark.parametrize("fid", ["does_not_exist", None])
def test_missing_ingredient_never_becomes_partial_total(catalog, recipe, fid):
    recipe.ingredients[0].food_id = fid
    result = calculate_recipe_nutrition(recipe, catalog)
    assert not result.complete
    assert all(v is None for v in result.totals.model_dump().values())
    assert result.issues


def test_unverified_food_not_used(catalog, recipe):
    catalog.foods["b"].review_status = "pending"
    result = calculate_recipe_nutrition(recipe, catalog)
    assert not result.complete and result.totals.kcal is None
    assert "unverified_food:b" in result.issues


def test_raw_and_cooked_are_distinct(catalog):
    raw = RecipeIngredient(ingredient_name="A", food_id="a", grams=100, state="raw")
    cooked = RecipeIngredient(ingredient_name="A", food_id="cooked", grams=100, state="cooked")
    assert calculate_nutrition([raw], catalog).totals.kcal == 100
    assert calculate_nutrition([cooked], catalog).totals.kcal == 300
    raw.state = "cooked"
    with pytest.raises(ValueError, match="Estado incompatible"):
        calculate_nutrition([raw], catalog)


@pytest.mark.parametrize("amount", [-1, 0, "-0.1", "NaN", "Infinity", "mucho", True, None])
def test_invalid_quantities(amount):
    with pytest.raises(ValidationError):
        RecipeIngredient(ingredient_name="A", food_id="a", grams=amount, state="raw")


@pytest.mark.parametrize("unit", ["kg", "ml", "cup", "unidad"])
def test_units_require_explicit_grams(unit):
    with pytest.raises(ValidationError):
        RecipeIngredient(ingredient_name="A", grams=1, unit=unit, state="raw")


@pytest.mark.parametrize("servings", [0, -1, True, 1.5, "2"])
def test_invalid_servings(catalog, recipe, servings):
    with pytest.raises(ValueError):
        calculate_nutrition(recipe.ingredients, catalog, servings=servings)


def test_empty_ingredients(catalog):
    with pytest.raises(ValueError, match="No hay"):
        calculate_nutrition([], catalog)


def test_rounding_is_half_up_and_preserves_internal_precision():
    values = NutrientValues(kcal="1.005", protein_g="0.0049", carbs_g=None)
    assert values.rounded()["kcal"] == "1.01"
    assert values.rounded()["protein_g"] == "0.00"
    assert values.rounded()["carbs_g"] is None
    assert values.kcal == Decimal("1.005")


@pytest.mark.parametrize("value", [-1, "NaN", "Infinity", True])
def test_invalid_nutrients(value):
    with pytest.raises(ValidationError):
        NutrientValues(kcal=value)
