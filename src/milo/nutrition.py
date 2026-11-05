from __future__ import annotations

from decimal import Decimal

from pydantic import TypeAdapter

from milo.catalog import FoodCatalog, FoodNotFoundError
from milo.models import (
    NutrientValues,
    NutritionResult,
    Positive,
    Recipe,
    RecipeIngredient,
    UserProfile,
    ValidationResult,
)

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


def adjust_portions(
    recipe: Recipe,
    target_kcal_per_serving: Decimal | str | float,
    catalog: FoodCatalog,
    *,
    profile: UserProfile | None = None,
    min_factor: Decimal = Decimal("0.5"),
    max_factor: Decimal = Decimal(2),
) -> Recipe:
    """Escala uniforme; no es un optimizador de macros ni una conversión crudo/cocinado."""
    target = TypeAdapter(Positive).validate_python(target_kcal_per_serving)
    lower = TypeAdapter(Positive).validate_python(min_factor)
    upper = TypeAdapter(Positive).validate_python(max_factor)
    if lower > upper:
        raise ValueError("Límites de escala invertidos")
    validation = validate_recipe(recipe, catalog, profile)
    if not validation.valid:
        raise ValueError("Receta no ajustable: " + "; ".join(validation.errors))
    nutrition = calculate_recipe_nutrition(recipe, catalog)
    current = nutrition.per_serving.kcal
    if not nutrition.complete or current is None or current == 0:
        raise ValueError("No se puede ajustar una receta sin energía completa y positiva")
    factor = target / current
    if not lower <= factor <= upper:
        raise ValueError(f"Objetivo fuera del rango práctico: factor {factor}")
    data = recipe.model_dump()
    for item in data["ingredients"]:
        item["grams"] *= factor
    data["review_status"] = "pending"
    data["notes"].append(f"Escala uniforme {factor}; conservar precisión y recalcular tras redondear pesos.")
    adjusted = Recipe.model_validate(data)
    if not validate_recipe(adjusted, catalog, profile).valid:
        raise ValueError("El ajuste no supera la validación")
    return adjusted
