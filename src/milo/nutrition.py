"""Catálogo de alimentos USDA y calculadora nutricional.

Todas las cifras salen de aquí: valor por 100 g × gramos / 100, sumado ingrediente a ingrediente.
Gemini nunca calcula macros; solo explica los resultados que devuelve este módulo.
"""

from __future__ import annotations

import csv
import json
import unicodedata
from decimal import Decimal
from pathlib import Path

from pydantic import TypeAdapter

from milo.models import (
    Food,
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
# Si un nombre coincide con varios estados del mismo alimento, prefiero el estado en que suelo pesarlo.
STATE_PREFERENCE = ["raw", "dry", "drained", "ready_to_eat", "cooked"]


# ---------------------------------------------------------------- Catálogo de alimentos


class FoodNotFoundError(LookupError):
    pass


class AmbiguousFoodError(LookupError):
    def __init__(self, query: str, options: list[Food]):
        self.options = options
        names = "; ".join(f"{f.food_id} = {f.name_es}" for f in options)
        super().__init__(f"'{query}' coincide con varios alimentos. Elige uno: {names}")


def normalize(text: str) -> str:
    """Minúsculas y sin tildes, para que 'platano' encuentre 'Plátano'."""
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def _words(text: str) -> list[str]:
    return [w for w in "".join(c if c.isalnum() else " " for c in normalize(text)).split() if len(w) > 2]


def _same_word(a: str, b: str) -> bool:
    # Comparo raíces para aceptar plurales: huevos/huevo, champiñones/champiñón.
    if a == b:
        return True
    root = min(len(a), len(b), 6)
    return root >= 4 and a[:root] == b[:root]


class FoodCatalog:
    def __init__(self, foods: list[Food]):
        self.foods = {food.food_id: food for food in foods}
        if len(self.foods) != len(foods):
            raise ValueError("food_id duplicado")

    @classmethod
    def from_csv(cls, path: str | Path) -> FoodCatalog:
        foods = []
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                nutrients = {
                    key: row.pop(key + "_100g") or None
                    for key in ["kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"]
                }
                for key in [
                    "allergens",
                    "nutrient_ids",
                    "nutrient_record_ids",
                    "allergen_review_complete",
                    "is_compound",
                    "vegan",
                    "vegetarian",
                ]:
                    row[key] = json.loads(row[key])
                row["fdc_id"] = int(row["fdc_id"]) if row["fdc_id"] else None
                foods.append(Food(**row, nutrients_per_100g=nutrients))
        return cls(foods)

    def lookup_food(self, query: str, *, state: str | None = None) -> Food:
        """Búsqueda exacta por food_id o por nombre completo."""
        if query in self.foods:
            matches = [self.foods[query]]
        else:
            matches = [
                f
                for f in self.foods.values()
                if query.strip().casefold() in {f.name_es.casefold(), f.name_source.casefold()}
            ]
        if state is not None:
            matches = [f for f in matches if f.state == state]
        if not matches:
            raise FoodNotFoundError(f"Alimento no encontrado: {query!r}, estado={state!r}")
        if len(matches) > 1:
            raise AmbiguousFoodError(query, matches)
        return matches[0]

    def search(self, text: str) -> list[Food]:
        """Alimentos cuyo nombre contiene todas las palabras buscadas (sin tildes, admite plurales)."""
        if text.strip() in self.foods:
            return [self.foods[text.strip()]]
        query = _words(text)
        if not query:
            return []
        found = []
        for food in self.foods.values():
            names = _words(food.name_es)
            if all(any(_same_word(q, n) for n in names) for q in query):
                found.append(food)
        return sorted(found, key=lambda f: (len(f.name_es), f.food_id))

    def resolve(self, text: str) -> Food:
        """Un único alimento para un nombre libre; si hay dudas reales, lanza AmbiguousFoodError."""
        found = self.search(text)
        if not found:
            raise FoodNotFoundError(f"No tengo '{text}' en mi catálogo USDA de 70 alimentos.")
        complete = [f for f in found if f.nutrients_per_100g.kcal is not None] or found
        if len(complete) == 1:
            return complete[0]
        # Mismo alimento en varios estados (pollo crudo / cocinado): elijo el estado habitual de pesado.
        best = min(STATE_PREFERENCE.index(f.state) for f in complete if f.state in STATE_PREFERENCE)
        preferred = [f for f in complete if f.state == STATE_PREFERENCE[best]]
        if len(preferred) == 1:
            return preferred[0]
        # "huevo" → prefiero "Huevo entero…" antes que "Clara de huevo…".
        first = _words(text)[0]
        starting = [f for f in preferred if _same_word(first, _words(f.name_es)[0])]
        if len(starting) == 1:
            return starting[0]
        raise AmbiguousFoodError(text, complete)


def load_catalog(path: Path | None = None) -> FoodCatalog:
    from milo.config import FOODS_CSV

    return FoodCatalog.from_csv(path or FOODS_CSV)


# ---------------------------------------------------------------- Calculadora


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
                # Un dato ausente no es cero: el total de ese nutriente queda desconocido.
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
    """Comprueba datos y restricciones con Python; el modelo de lenguaje no decide esto."""
    errors, warnings, allergens = [], [], set()
    has_allergy = profile is not None and any(
        r.kind in {"allergy", "intolerance"} for r in profile.restrictions
    )
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
            # Producto comercial (pan, pasta, conservas, tofu): sus alérgenos dependen de la marca.
            # Para un perfil con alergias no lo doy por seguro; para el resto, aviso de revisar la etiqueta.
            if has_allergy:
                errors.append(f"allergens_pending:{food.food_id}")
            else:
                warnings.append(f"Revisa la etiqueta de la marca: {food.name_es}.")
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


def round_grams(grams: Decimal) -> Decimal:
    """Pesos cómodos de cocina: de 1 en 1 g por debajo de 20 g y de 5 en 5 g por encima."""
    step = Decimal(1) if grams < 20 else Decimal(5)
    return max(step, (grams / step).quantize(Decimal(1)) * step)


def scale_recipe(recipe: Recipe, factor: Decimal | str | float, *, rounded: bool = False) -> Recipe:
    """Multiplica todos los gramos por el mismo factor. Con rounded=True dejo pesos fáciles de medir."""
    factor = TypeAdapter(Positive).validate_python(factor)
    data = recipe.model_dump()
    for item in data["ingredients"]:
        item["grams"] = round_grams(item["grams"] * factor) if rounded else item["grams"] * factor
    return Recipe.model_validate(data)


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
        raise ValueError(
            f"Objetivo fuera del rango práctico: tendría que multiplicar las cantidades por {factor:.2f} "
            f"(admito entre {lower} y {upper})."
        )
    adjusted = scale_recipe(recipe, factor)
    adjusted.review_status = "pending"
    adjusted.notes.append(f"Escala uniforme {factor}; conservar precisión y recalcular tras redondear pesos.")
    if not validate_recipe(adjusted, catalog, profile).valid:
        raise ValueError("El ajuste no supera la validación")
    return adjusted
