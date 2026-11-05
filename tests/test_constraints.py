from decimal import Decimal

import pytest
from pydantic import ValidationError

from milo.models import DietaryRestriction, UserProfile
from milo.nutrition import (
    AmbiguousFoodError,
    FoodNotFoundError,
    adjust_portions,
    calculate_recipe_nutrition,
    validate_recipe,
)


def test_lookup_explicit_and_ambiguous(catalog):
    assert catalog.lookup_food("a").name_es == "Alimento A"
    assert catalog.lookup_food("Alimento A", state="cooked").food_id == "cooked"
    with pytest.raises(AmbiguousFoodError):
        catalog.lookup_food("Alimento A")
    with pytest.raises(FoodNotFoundError):
        catalog.lookup_food("inexistente")


def test_free_text_resolution(catalog, real_catalog):
    assert catalog.resolve("a").food_id == "a"
    with pytest.raises(AmbiguousFoodError):
        catalog.resolve("alimento")
    # Mismo alimento crudo y cocinado: elijo el estado en que se suele pesar.
    assert real_catalog.resolve("pechuga de pollo").state == "raw"
    # Con pechuga y muslo crudos en el catálogo, "pollo" es ambiguo: MILO pide que elija.
    with pytest.raises(AmbiguousFoodError):
        real_catalog.resolve("pollo")
    assert real_catalog.resolve("huevos").name_es.startswith("Huevo entero")
    with pytest.raises(FoodNotFoundError):
        catalog.resolve("caviar")


@pytest.mark.parametrize("kind", ["allergy", "intolerance"])
def test_known_allergens(catalog, recipe, kind):
    catalog.foods["a"].allergens = {"egg"}
    profile = UserProfile(user_id="test", restrictions=[DietaryRestriction(kind=kind, value="egg")])
    result = validate_recipe(recipe, catalog, profile)
    assert not result.valid and "egg" in result.allergens
    assert "allergen_conflict:a:egg" in result.errors


def test_commercial_product_warns_and_blocks_only_with_allergies(catalog, recipe):
    catalog.foods["a"].is_compound = True
    catalog.foods["a"].allergen_review_complete = False
    result = validate_recipe(recipe, catalog)
    assert result.valid and any("etiqueta" in w for w in result.warnings)
    allergic = UserProfile(restrictions=[DietaryRestriction(kind="allergy", value="milk")])
    result = validate_recipe(recipe, catalog, allergic)
    assert not result.valid and "allergens_pending:a" in result.errors


@pytest.mark.parametrize("value", [False, None])
def test_diet_incompatible_or_unknown(catalog, recipe, value):
    catalog.foods["a"].vegan = value
    profile = UserProfile(user_id="test", restrictions=[DietaryRestriction(kind="diet", value="vegan")])
    assert not validate_recipe(recipe, catalog, profile).valid


def test_dislikes_and_exclusions(catalog, recipe):
    profile = UserProfile(
        user_id="test",
        disliked_food_ids={"a"},
        restrictions=[DietaryRestriction(kind="exclude_food", value="b")],
    )
    result = validate_recipe(recipe, catalog, profile)
    assert "disliked_food:a" in result.errors and "excluded_food:b" in result.errors


def test_unknown_restrictions_fail_closed():
    with pytest.raises(ValidationError):
        DietaryRestriction(kind="allergy", value="unknown")


def test_adjustment_preserves_original_and_recalculates(catalog, recipe):
    adjusted = adjust_portions(recipe, 150, catalog)
    assert recipe.ingredients[0].grams == 100
    assert adjusted.ingredients[0].grams == 150
    assert calculate_recipe_nutrition(adjusted, catalog).per_serving.kcal == 150


def test_adjustment_enforces_restrictions(catalog, recipe):
    profile = UserProfile(user_id="test", disliked_food_ids={"a"})
    with pytest.raises(ValueError, match="no ajustable"):
        adjust_portions(recipe, 150, catalog, profile=profile)


@pytest.mark.parametrize("target", [0, -1, "NaN", True, 1000])
def test_adjustment_invalid_or_impractical(catalog, recipe, target):
    with pytest.raises(ValueError):
        adjust_portions(recipe, target, catalog)


def test_adjustment_missing_calories(catalog, recipe):
    catalog.foods["a"].nutrients_per_100g.kcal = None
    with pytest.raises(ValueError):
        adjust_portions(recipe, 150, catalog)


def test_adjustment_fractional_no_early_rounding(catalog, recipe):
    adjusted = adjust_portions(recipe, Decimal("133.333"), catalog)
    assert calculate_recipe_nutrition(adjusted, catalog).per_serving.kcal == Decimal("133.333")
