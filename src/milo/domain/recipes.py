from decimal import Decimal

from pydantic import TypeAdapter

from milo.domain.constraints import validate_recipe
from milo.domain.nutrition import calculate_recipe_nutrition
from milo.models import Positive, Recipe, UserProfile
from milo.repositories.catalog import FoodCatalog


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
