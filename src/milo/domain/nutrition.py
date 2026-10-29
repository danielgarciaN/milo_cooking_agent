from __future__ import annotations

from decimal import Decimal

from milo.models import NutrientValues, NutritionResult, Recipe, RecipeIngredient
from milo.repositories.catalog import FoodCatalog, FoodNotFoundError

REQUIRED_NUTRIENTS = ("kcal", "protein_g", "carbs_g", "fat_g")
NUTRIENTS = (*REQUIRED_NUTRIENTS, "fiber_g")


def calculate_nutrition(
    ingredients: list[RecipeIngredient], catalog: FoodCatalog, *, servings: int = 1
) -> NutritionResult:
    if isinstance(servings, bool) or not isinstance(servings, int) or servings <= 0:
        raise ValueError("Las raciones deben ser un entero positivo")
    if not ingredients:
        raise ValueError("No hay ingredientes")
    totals = dict.fromkeys(NUTRIENTS, Decimal(0))
    missing: dict[str, list[str]] = {}
    issues, ids = [], []
    for i, ingredient in enumerate(ingredients):
        # Revalidar objetos también protege ante objetos construidos con model_construct/copy.
        item = RecipeIngredient.model_validate(ingredient.model_dump())
        key = f"{i}:{item.ingredient_name}"
        food = None
        if item.food_id is not None:
            try:
                food = catalog.lookup_food(item.food_id)
            except FoodNotFoundError:
                issues.append(f"unknown_food:{item.food_id}")
        else:
            issues.append(f"unresolved_food:{item.ingredient_name}")
        if food is not None and (food.state != item.state or item.state == "unknown"):
            raise ValueError(f"Estado incompatible para {item.ingredient_name}: {item.state} / {food.state}")
        if food is not None and food.review_status != "verified":
            issues.append(f"unverified_food:{food.food_id}")
            food = None
        if food is not None:
            ids.append(food.food_id)
        absent = []
        for nutrient in NUTRIENTS:
            value = getattr(food.nutrients_per_100g, nutrient) if food else None
            if value is None:
                absent.append(nutrient)
                totals[nutrient] = None
            elif totals[nutrient] is not None:
                totals[nutrient] += item.grams * value / Decimal(100)
        if absent:
            missing[key] = absent
    per_serving = {key: value / servings if value is not None else None for key, value in totals.items()}
    return NutritionResult(
        totals=NutrientValues(**totals),
        per_serving=NutrientValues(**per_serving),
        servings=servings,
        complete=all(totals[key] is not None for key in REQUIRED_NUTRIENTS),
        missing=missing,
        issues=issues,
        food_ids=ids,
    )


def calculate_recipe_nutrition(recipe: Recipe, catalog: FoodCatalog) -> NutritionResult:
    return calculate_nutrition(recipe.ingredients, catalog, servings=recipe.servings)
