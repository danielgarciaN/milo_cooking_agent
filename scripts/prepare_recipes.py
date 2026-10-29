"""Transforma los borradores con decisiones editoriales explícitas y valida con Python."""

import json
from pathlib import Path

from milo.domain.constraints import validate_recipe
from milo.domain.nutrition import calculate_recipe_nutrition
from milo.models import Recipe, RecipeIngredient
from milo.repositories.catalog import FoodCatalog

ROOT = Path(__file__).resolve().parents[1]

# IDs concretos, sin emparejamiento semántico automático ni conversiones de peso.
MAPPING = {
    "pollo pechuga": 2646170,
    "arroz": 2512381,
    "tomate": 1999634,
    "aceite de oliva": 171413,
    "huevo entero": 748967,
    "espinacas": 1999632,
    "avena": 2346396,
    "yogur natural": 2259793,
    "plátano": 1105314,
    "pasta seca": 2758998,
    "atún al natural escurrido": 334194,
    "tomate triturado": 2685581,
    "garbanzo cocido escurrido": 2644288,
    "pepino": 2346406,
    "salmón": 2684441,
    "patata": 2346401,
    "brócoli": 747447,
    "pan integral": 2758994,
    "aguacate": 2710824,
    "lentejas cocidas": 172421,
    "zanahoria": 2258586,
    "cebolla": 790646,
    "tortilla de trigo": 2758996,
    "pavo cocinado": 746785,
    "lechuga": 2346389,
    "champiñones": 1999629,
    "tofu firme": 172475,
    "calabacín": 2685568,
    "nueces": 2346394,
}
STEPS = {
    "r001": [
        "Pesar el arroz en seco y la pechuga cruda, sin piel ni hueso. Lavar y cortar el tomate.",
        "Cocer el arroz en agua siguiendo el tiempo del envase; escurrir si sobra agua.",
        "Cortar el pollo en tiras. Calentar el aceite medido en una sartén y cocinar el pollo hasta alcanzar 74 °C en el centro, medidos con termómetro.",
        "Servir el arroz con el pollo y el tomate. Incorporar el aceite y jugos de la sartén que se vayan a consumir.",
    ],
    "r002": [
        "Pesar el huevo sin cáscara. Lavar las espinacas y secarlas.",
        "Calentar el aceite medido en una sartén antiadherente y saltear las espinacas hasta que pierdan volumen.",
        "Batir el huevo, añadirlo y cuajar la tortilla por ambos lados; comprobar 71 °C en el centro.",
        "Servir la tortilla completa como una ración.",
    ],
    "r003": [
        "Pesar el plátano pelado y cortarlo en rodajas.",
        "Mezclar los copos de avena aptos para consumo sin cocción con el yogur; si el envase exige cocción, cocerlos antes en agua y dejar templar.",
        "Añadir el plátano y servir. El agua de cocción no cambia los gramos de avena seca contabilizados.",
    ],
    "r004": [
        "Pesar los espaguetis secos. Escurrir el atún y pesar solo los sólidos.",
        "Cocer la pasta en agua según el envase. Calentar el aceite y cocinar el tomate triturado durante unos 8 minutos a fuego medio.",
        "Añadir el atún y calentar la salsa. Mezclar con la pasta escurrida y servir.",
    ],
    "r005": [
        "Utilizar garbanzos en conserva listos para consumir; enjuagarlos, escurrirlos y pesar 200 g de sólidos.",
        "Lavar el pepino y el tomate y cortarlos en dados, manteniendo la piel del pepino.",
        "Mezclar las verduras con los garbanzos y el aceite pesado. Servir frío.",
    ],
    "r006": [
        "Precalentar el horno a 200 °C. Pesar la patata pelada cruda, el brócoli limpio y el salmón crudo comestible.",
        "Cortar la patata en láminas finas, repartir parte del aceite y hornear unos 20 minutos.",
        "Añadir el brócoli en ramilletes y el salmón con el aceite restante; continuar hasta que la patata esté tierna y el pescado alcance 63 °C en el centro.",
        "Servir todo como una ración. El tiempo es orientativo y depende del grosor; comprobar con termómetro.",
    ],
    "r007": [
        "Pesar el pan antes de tostarlo y el aguacate pelado sin hueso.",
        "Pesar el huevo sin cáscara y cuajarlo en una sartén antiadherente sin aceite añadido, hasta 71 °C en el centro.",
        "Tostar el pan, repartir el aguacate machacado y colocar el huevo encima.",
    ],
    "r008": [
        "Usar lentejas previamente hervidas sin sal y pesar 250 g cocidos, sin exceso de agua libre; no sustituir por 250 g secos.",
        "Pelar y picar la cebolla y la zanahoria. Rehogarlas con el aceite medido a fuego medio.",
        "Añadir agua en pequeñas cantidades y cocinar hasta que la zanahoria esté tierna. Incorporar las lentejas, calentar y servir con el líquido del guiso.",
    ],
    "r009": [
        "Esta versión utiliza pavo picado 93% magro ya cocinado en sartén; pesar 140 g después de cocinar. Si se parte de crudo, cocinar hasta 74 °C y pesar después, sin estimar rendimiento.",
        "Lavar y cortar la lechuga y el tomate. Calentar la tortilla de trigo siguiendo el envase.",
        "Repartir el pavo, la lechuga y el tomate sobre la tortilla y enrollarla. No añadir salsas no contabilizadas.",
    ],
    "r010": [
        "Limpiar los champiñones y laminarlos. Pesar los huevos sin cáscara y batirlos.",
        "Calentar el aceite medido, añadir los champiñones y saltear hasta que reduzcan su agua.",
        "Añadir el huevo y remover a fuego medio hasta que el revuelto alcance 71 °C; servir.",
    ],
    "r011": [
        "Pesar el arroz seco y el tofu firme con sulfato cálcico tal como se consume, sin líquido libre ni prensado adicional. Lavar y cortar las verduras.",
        "Cocer el arroz en agua según el envase. Cortar el tofu en dados.",
        "Calentar el aceite medido y saltear la zanahoria en tiras finas y el calabacín. Añadir el tofu y cocinar según las instrucciones de su envase.",
        "Mezclar con el arroz cocido y servir. No se han incluido salsa de soja ni otros condimentos energéticos.",
    ],
    "r012": [
        "Esta versión concreta los frutos rojos del borrador en 50 g de fresas y 50 g de frambuesas; no presupone una mezcla comercial.",
        "Lavar las frutas, retirar partes no comestibles y pesar las cantidades indicadas. Trocear las fresas.",
        "Servir el yogur con la fruta y 25 g de nueces sin cáscara, troceadas.",
    ],
}


def main():
    catalog = FoodCatalog.from_csv(ROOT / "data/structured/foods.csv")
    drafts = json.loads((ROOT / "data/structured/recipes_DRAFT.json").read_text(encoding="utf-8"))
    recipes, reports, results = [], [], {}
    for draft in drafts:
        ingredients = []
        notes = [
            "Adaptación editorial MILO de un borrador del usuario, no receta oficial USDA.",
            "Pesos de porción comestible; sin conversión automática crudo/cocinado.",
            "Nutrición estimada por suma de ingredientes, sin retención ni rendimiento de cocción.",
        ]
        for item in draft["ingredients"]:
            if item["ingredient_name"] == "frutos rojos":
                for fid in [2346409, 2346410]:
                    food = catalog.lookup_food(f"fdc_{fid}")
                    ingredients.append(
                        RecipeIngredient(
                            ingredient_name=food.name_es,
                            food_id=food.food_id,
                            grams=50,
                            state=food.state,
                            notes="Mezcla editorial 50/50 explícita.",
                        )
                    )
                notes.append(
                    "Frutos rojos concretados en fresas y frambuesas; no equivalencia para otras mezclas."
                )
                continue
            food = catalog.lookup_food(f"fdc_{MAPPING[item['ingredient_name']]}")
            ingredients.append(
                RecipeIngredient(
                    ingredient_name=food.name_es,
                    food_id=food.food_id,
                    grams=item["grams"],
                    state=food.state,
                    notes=f"Borrador: {item['ingredient_name']}. Peso en estado {food.state}.",
                )
            )
        if draft["recipe_id"] == "r009":
            notes.append(
                "Pavo cocinado concretado en pavo picado, no fiambre ni pechuga; modificación editorial explícita."
            )
        if any(item["ingredient_name"] == "aceite de oliva" for item in draft["ingredients"]):
            notes.append(
                "Aceite de oliva genérico SR Legacy 171413; no se imputan los datos al AOVE Foundation 748608."
            )
        recipe = Recipe(
            recipe_id=draft["recipe_id"],
            title=draft["title"],
            servings=draft["servings"],
            ingredients=ingredients,
            steps=STEPS[draft["recipe_id"]],
            time_minutes_estimate=40 if draft["recipe_id"] == "r006" else draft["time_minutes_estimate"],
            tags=[
                tag for tag in draft["tags"] if tag not in {"high_protein", "vegan", "vegetarian", "budget"}
            ],
            notes=notes,
        )
        validation = validate_recipe(recipe, catalog)
        recipe.allergens = validation.allergens
        recipe.review_status = "verified" if validation.valid else "pending"
        nutrition = calculate_recipe_nutrition(recipe, catalog)
        recipes.append(recipe.model_dump(mode="json"))
        reports.append(
            {
                "recipe_id": recipe.recipe_id,
                "status": recipe.review_status,
                **validation.model_dump(mode="json"),
                "nutrition_complete": nutrition.complete,
            }
        )
        results[recipe.recipe_id] = nutrition.model_dump(mode="json")
    (ROOT / "data/structured/recipes.json").write_text(
        json.dumps(recipes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "data/structured/recipe_nutrition.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = {
        "count": len(recipes),
        "verified": sum(r["status"] == "verified" for r in reports),
        "pending": sum(r["status"] != "verified" for r in reports),
        "recipes": reports,
        "cooking_reference": "https://www.foodsafety.gov/food-safety-charts/safe-minimum-internal-temperatures",
    }
    (ROOT / "evaluation/recipe_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"Recetas: {summary['count']}; verificadas: {summary['verified']}; pendientes: {summary['pending']}"
    )


if __name__ == "__main__":
    main()
