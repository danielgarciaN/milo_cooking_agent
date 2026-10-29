from decimal import Decimal

import pytest
from pydantic import ValidationError

from milo.domain.constraints import validate_recipe
from milo.domain.nutrition import calculate_recipe_nutrition
from milo.domain.recipes import adjust_portions
from milo.models import DietaryRestriction, UserProfile
from milo.repositories.catalog import AmbiguousFoodError, FoodNotFoundError, lookup_food


def test_lookup_explicit_and_ambiguous(catalog):
    assert lookup_food("a", catalog).name_es == "Alimento A"
    assert lookup_food("Alimento A", catalog, state="cooked").food_id == "cooked"
    with pytest.raises(AmbiguousFoodError):
        lookup_food("Alimento A", catalog)
    with pytest.raises(FoodNotFoundError):
        lookup_food("inexistente", catalog)


@pytest.mark.parametrize("kind", ["allergy", "intolerance"])
def test_known_allergens(catalog, recipe, kind):
    catalog.foods["a"].allergens = {"egg"}
    profile = UserProfile(user_id="test", restrictions=[DietaryRestriction(kind=kind, value="egg")])
    result = validate_recipe(recipe, catalog, profile)
    assert not result.valid and "egg" in result.allergens
    assert "allergen_conflict:a:egg" in result.errors


def test_compound_unknown_allergens_blocks_validation(catalog, recipe):
    catalog.foods["a"].is_compound = True
    catalog.foods["a"].allergen_review_complete = False
    result = validate_recipe(recipe, catalog)
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
