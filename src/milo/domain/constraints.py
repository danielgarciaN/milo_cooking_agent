from milo.domain.nutrition import REQUIRED_NUTRIENTS
from milo.models import Recipe, UserProfile, ValidationResult
from milo.repositories.catalog import FoodCatalog, FoodNotFoundError


def validate_recipe(
    recipe: Recipe, catalog: FoodCatalog, profile: UserProfile | None = None
) -> ValidationResult:
    errors, warnings, allergens = [], [], set()
    for item in recipe.ingredients:
        if item.food_id is None:
            errors.append(f"unresolved_food:{item.ingredient_name}")
            continue
        try:
            food = catalog.lookup_food(item.food_id)
        except FoodNotFoundError:
            errors.append(f"unknown_food:{item.food_id}")
            continue
        allergens.update(food.allergens)
        if food.review_status != "verified":
            errors.append(f"unverified_food:{food.food_id}")
        if item.state != food.state or item.state == "unknown":
            errors.append(f"state_mismatch:{food.food_id}")
        for key in REQUIRED_NUTRIENTS:
            if getattr(food.nutrients_per_100g, key) is None:
                errors.append(f"missing_nutrient:{food.food_id}:{key}")
        if not food.allergen_review_complete:
            errors.append(f"allergens_pending:{food.food_id}")
        if food.is_compound:
            warnings.append(f"compound_food:comprobar composición de la marca concreta:{food.food_id}")
        if profile is None:
            continue
        if food.food_id in profile.disliked_food_ids:
            errors.append(f"disliked_food:{food.food_id}")
        for restriction in profile.restrictions:
            if restriction.kind in {"allergy", "intolerance"} and restriction.value in food.allergens:
                errors.append(f"allergen_conflict:{food.food_id}:{restriction.value}")
            if restriction.kind == "exclude_food" and restriction.value == food.food_id:
                errors.append(f"excluded_food:{food.food_id}")
            if restriction.kind == "diet" and getattr(food, restriction.value) is not True:
                errors.append(f"diet_conflict_or_unknown:{food.food_id}:{restriction.value}")
    warnings.append(
        "Alérgenos deducidos del alimento; no acredita ausencia de trazas ni contaminación cruzada."
    )
    return ValidationResult(valid=not errors, errors=errors, warnings=warnings, allergens=allergens)
