"""Valido data/recipes.json y regenero el documento del recetario que se indexa en el RAG.

Ejecuto este script cada vez que añado o modifico una receta:
    python scripts/prepare_recipes.py
Después reconstruyo el índice:  python scripts/build_index.py
"""

import hashlib
import json

from milo.config import DOCUMENTS_DIR, RECIPES_JSON, ROOT, SOURCES_JSON
from milo.models import Recipe
from milo.nutrition import calculate_recipe_nutrition, load_catalog, validate_recipe

INTRO = """# Recetario de MILO

He preparado este recetario para el proyecto MILO. Son recetas caseras sencillas, pensadas para una
ración, que utilizan únicamente alimentos de mi catálogo nutricional (USDA FoodData Central). Las
cantidades son de porción comestible y distinguen el estado en que se pesa cada ingrediente:
crudo, seco, escurrido o ya cocinado. No es lo mismo 80 g de arroz seco que 80 g de arroz cocido.

No escribo calorías ni macros en este documento: MILO las calcula con Python a partir de los
valores por 100 g de cada ingrediente, para que nunca dependan de lo que recuerde el modelo de
lenguaje. Las temperaturas de cocción segura siguen FoodSafety.gov
(https://www.foodsafety.gov/food-safety-charts/safe-minimum-internal-temperatures): aves 74 °C,
carne picada 71 °C, preparaciones con huevo 71 °C y pescado y marisco 63 °C.

Los alérgenos indicados son los propios de cada alimento. No garantizan la ausencia de trazas: en
productos comerciales (pan, pasta, conservas, tofu) hay que revisar siempre la etiqueta de la marca.
"""

MEALS = {"desayuno": "desayuno", "comida": "comida", "cena": "cena", "snack": "tentempié"}
ALLERGENS_ES = {
    "milk": "leche", "egg": "huevo", "fish": "pescado", "crustacean": "crustáceos", "mollusc": "moluscos",
    "soy": "soja", "wheat": "trigo", "gluten": "gluten", "peanut": "cacahuete", "tree_nuts": "frutos secos",
    "sesame": "sésamo", "celery": "apio", "mustard": "mostaza", "lupin": "altramuz", "sulphites": "sulfitos",
}  # fmt: skip


def main():
    catalog = load_catalog()
    raw = json.loads(RECIPES_JSON.read_text(encoding="utf-8"))
    recipes, text = [], [INTRO]
    for item in raw:
        recipe = Recipe.model_validate(item)
        validation = validate_recipe(recipe, catalog)
        nutrition = calculate_recipe_nutrition(recipe, catalog)
        recipe.allergens = validation.allergens
        recipe.review_status = "verified" if validation.valid and nutrition.complete else "pending"
        recipes.append(recipe.model_dump(mode="json"))
        print(f"{recipe.recipe_id} {recipe.review_status:8} {recipe.title}", *validation.errors)
        if recipe.review_status != "verified":
            continue
        foods = [catalog.lookup_food(i.food_id) for i in recipe.ingredients]
        diet = (
            "vegana" if all(f.vegan for f in foods)
            else "vegetariana" if all(f.vegetarian for f in foods)
            else "con productos animales o de composición según marca"
        )  # fmt: skip
        meals = ", ".join(MEALS[t] for t in recipe.tags if t in MEALS)
        allergens = ", ".join(ALLERGENS_ES[a] for a in sorted(recipe.allergens)) or "ninguno conocido"
        text.append(f"## {recipe.recipe_id} — {recipe.title}\n")
        text.append(
            f"Receta para {recipe.servings} ración. Ideal para: {meals}. Tiempo orientativo: "
            f"{recipe.time_minutes_estimate} minutos. Dificultad: {recipe.difficulty}. Dieta: {diet}.\n"
        )
        text.append("Ingredientes y cantidades:\n")
        text.extend(f"- {i.ingredient_name}: {i.grams} g ({i.food_id})." for i in recipe.ingredients)
        text.append("\nPreparación:\n")
        text.extend(f"{n}. {step}" for n, step in enumerate(recipe.steps, start=1))
        text.append(f"\nAlérgenos propios de los ingredientes: {allergens}.\n")
    RECIPES_JSON.write_text(json.dumps(recipes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    document = DOCUMENTS_DIR / "recetario_milo.md"
    document.write_text("\n".join(text), encoding="utf-8")

    # Actualizo el hash de los documentos propios: el RAG comprueba que el archivo no ha cambiado sin registrarse.
    sources = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
    for source in sources:
        if source["file_type"] == "markdown" and source["path"]:
            data = (ROOT / source["path"]).read_bytes()
            source.update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
    SOURCES_JSON.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verified = sum(r["review_status"] == "verified" for r in recipes)
    print(f"\n{verified}/{len(recipes)} recetas verificadas → {document.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
