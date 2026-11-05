"""Exporto recetas revisadas y registro los documentos propios del RAG."""

import hashlib
import json

from milo.catalog import FoodCatalog
from milo.config import ROOT
from milo.models import DataSource, Recipe
from milo.nutrition import validate_recipe


def main():
    folder = ROOT / "data/documents"
    folder.mkdir(parents=True, exist_ok=True)
    catalog = FoodCatalog.from_csv(ROOT / "data/structured/foods.csv")
    recipes = [
        Recipe.model_validate(r)
        for r in json.loads((ROOT / "data/structured/recipes.json").read_text(encoding="utf-8"))
    ]
    text = [
        "# Mi recetario revisado para MILO\n",
        "He preparado este documento a partir de mi recetario estructurado. Incluyo solo recetas que superan la revisión de ingredientes, estados, nutrientes esenciales y alérgenos conocidos. Son adaptaciones propias del proyecto, no publicaciones de USDA. La revisión utiliza datos y código; no equivale a un ensayo físico de cocina.\n",
        "Todas las cantidades son de porción comestible. Distingo pesos secos, crudos y cocinados. Calculo los macros con Python desde el catálogo USDA; no añado cifras editadas manualmente a este documento. Los ingredientes distintos requieren un nuevo cálculo.\n",
        "Referencias: FoodData Central (https://fdc.nal.usda.gov/) para los datos de alimentos; FoodSafety.gov (https://www.foodsafety.gov/food-safety-charts/safe-minimum-internal-temperatures) para temperaturas. Los alérgenos conocidos no acreditan ausencia de trazas.\n",
    ]
    count = 0
    for recipe in recipes:
        validation = validate_recipe(recipe, catalog)
        if recipe.review_status != "verified" or not validation.valid:
            continue
        count += 1
        text.append(f"## {recipe.recipe_id} — {recipe.title}\n")
        text.append(
            f"He revisado esta receta para {recipe.servings} ración. Tiempo orientativo: {recipe.time_minutes_estimate} minutos. Para solicitar sus macros utilizo el ID {recipe.recipe_id}.\n"
        )
        text.append("Ingredientes y cantidades:\n")
        text.extend(f"- {i.ingredient_name}: {i.grams} g; registro {i.food_id}." for i in recipe.ingredients)
        text.append("\nPreparación:\n")
        text.extend(f"{i}. {step}" for i, step in enumerate(recipe.steps, start=1))
        allergens = (
            ", ".join(sorted(validation.allergens))
            or "ninguno identificado en los ingredientes de referencia"
        )
        text.append(
            f"\nAlérgenos conocidos: {allergens}. Esto no garantiza ausencia de trazas ni sustituye la etiqueta del producto.\n"
        )
        text.append(
            "He conservado el estado de pesado de cada ingrediente. Si cambio una cantidad o un alimento, vuelvo a validar y calcular; no considero equivalentes pesos crudos y cocinados.\n"
        )
    (folder / "recetas_revisadas.md").write_text("\n".join(text), encoding="utf-8")
    sources_path = ROOT / "data/sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    for sid, name, title in [
        ("MILO_RECETAS", "recetas_revisadas.md", "Mi recetario revisado para MILO"),
        ("MILO_TECNICAS", "tecnicas_y_sustituciones.md", "Técnicas culinarias y sustituciones para MILO"),
    ]:
        path = folder / name
        data = path.read_bytes()
        source = DataSource(
            source_id=sid,
            title=title,
            url=path.relative_to(ROOT).as_posix(),
            file_type="markdown",
            version="2026-10-30",
            status="created",
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            path=path.relative_to(ROOT).as_posix(),
            usage_conditions="Documento propio del proyecto; referencias externas identificadas.",
            usage="rag_general",
        )
        sources = [s for s in sources if s["source_id"] != sid]
        sources.append(source.model_dump())
    sources_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Documento con {count} recetas revisadas; dos documentos propios registrados junto a AESAN.")


if __name__ == "__main__":
    main()
