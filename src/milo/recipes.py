"""Herramientas de cocina de MILO. Todo es Python determinista: aquí no interviene Gemini.

- buscar recetas (también en modo "Mi nevera"),
- ver una receta con sus macros, cambiar raciones o ajustarla a unas kcal,
- sustituir un ingrediente y recalcular,
- calcular un plato libre,
- crear un menú semanal y su lista de la compra,
- actualizar el perfil (dieta, alergias, alimentos que no gustan, objetivo).

Cada función devuelve un diccionario sencillo que el agente pasa a Gemini y que la app pinta como tarjeta.
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

from milo.config import RECIPES_JSON
from milo.models import DietaryRestriction, Recipe, RecipeIngredient, UserProfile
from milo.nutrition import (
    AmbiguousFoodError,
    FoodCatalog,
    FoodNotFoundError,
    _same_word,
    _words,
    adjust_portions,
    calculate_nutrition,
    load_catalog,
    round_grams,
    scale_recipe,
    validate_recipe,
)

ALLERGENS_ES = {
    "milk": "leche", "egg": "huevo", "fish": "pescado", "crustacean": "crustáceos", "mollusc": "moluscos",
    "soy": "soja", "wheat": "trigo", "gluten": "gluten", "peanut": "cacahuete", "tree_nuts": "frutos secos",
    "sesame": "sésamo", "celery": "apio", "mustard": "mostaza", "lupin": "altramuz", "sulphites": "sulfitos",
}  # fmt: skip
# Lo que el usuario puede escribir → código de alérgeno del catálogo.
ALLERGEN_INPUT = {
    **{v: k for k, v in ALLERGENS_ES.items()},
    "lactosa": "milk", "lacteos": "milk", "huevos": "egg", "marisco": "crustacean", "gambas": "crustacean",
    "nueces": "tree_nuts", "almendras": "tree_nuts", "cacahuetes": "peanut", "mani": "peanut",
    "celiaquia": "gluten", "trigo": "wheat", "soja": "soy",
}  # fmt: skip
DIETS = {"vegetariana": "vegetarian", "vegetariano": "vegetarian", "vegana": "vegan", "vegano": "vegan"}
MEAL_NAMES = {"desayuno": "Desayuno", "comida": "Comida", "cena": "Cena", "snack": "Snack"}
DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
# Reparto orientativo de la energía diaria entre las comidas del menú.
SHARES = {
    3: {"desayuno": Decimal("0.30"), "comida": Decimal("0.40"), "cena": Decimal("0.30")},
    4: {"desayuno": Decimal("0.25"), "comida": Decimal("0.35"), "cena": Decimal("0.30"), "snack": Decimal("0.10")},
}  # fmt: skip
PANTRY = ("fdc_171413", "fdc_1104647")  # Aceite de oliva y ajo: doy por hecho que hay en casa.
SHOPPING_CATEGORIES = [
    ("Carne, pescado y marisco", ["pollo", "pavo", "vacuno", "salmon", "bacalao", "atun", "gamba"]),
    ("Huevos y lácteos", ["huevo", "clara", "leche", "yogur", "queso"]),
    ("Cereales, pan y pasta", ["arroz", "espagueti", "avena", "pan", "tortilla comercial", "quinoa"]),
    ("Legumbres y tofu", ["garbanzo", "alubia", "lenteja", "tofu", "soja"]),
    ("Frutos secos y semillas", ["nuez", "almendra", "anacardo", "cacahuete", "pipas"]),
    ("Aceites", ["aceite"]),
]


def _num(value, places: int = 1) -> float | None:
    return None if value is None else float(round(Decimal(value), places))


def _macros(values) -> dict:
    return {
        "kcal": _num(values.kcal, 0),
        "protein_g": _num(values.protein_g),
        "carbs_g": _num(values.carbs_g),
        "fat_g": _num(values.fat_g),
        "fiber_g": _num(values.fiber_g),
    }


class Kitchen:
    def __init__(self, catalog: FoodCatalog | None = None, recipes: list[Recipe] | None = None):
        self.catalog = catalog or load_catalog()
        if recipes is None:
            raw = json.loads(RECIPES_JSON.read_text(encoding="utf-8"))
            recipes = [Recipe.model_validate(r) for r in raw]
        self.recipes = {r.recipe_id: r for r in recipes if r.review_status == "verified"}

    # ------------------------------------------------------------ utilidades

    def diet_label(self, recipe: Recipe) -> str:
        foods = [self.catalog.lookup_food(i.food_id) for i in recipe.ingredients]
        if all(f.vegan for f in foods):
            return "vegana"
        if all(f.vegetarian for f in foods):
            return "vegetariana"
        return "omnívora"

    def card(self, recipe: Recipe, profile: UserProfile | None = None, **extra) -> dict:
        """Ficha completa de una receta con macros calculados por Python."""
        nutrition = calculate_nutrition(recipe.ingredients, self.catalog, servings=recipe.servings)
        validation = validate_recipe(recipe, self.catalog, profile)
        return {
            "tipo": "receta",
            "recipe_id": recipe.recipe_id,
            "titulo": recipe.title,
            "raciones": recipe.servings,
            "tiempo_min": recipe.time_minutes_estimate,
            "dificultad": recipe.difficulty,
            "comidas": [t for t in recipe.tags if t in MEAL_NAMES],
            "dieta": self.diet_label(recipe),
            "ingredientes": [
                {
                    "nombre": i.ingredient_name,
                    "gramos": _num(i.grams, 0),
                    "food_id": i.food_id,
                    "estado": i.state,
                }
                for i in recipe.ingredients
            ],
            "pasos": recipe.steps,
            "por_racion": _macros(nutrition.per_serving),
            "total": _macros(nutrition.totals),
            "alergenos": sorted(ALLERGENS_ES[a] for a in validation.allergens),
            "avisos": validation.warnings[:-1],
            "compatible_con_perfil": validation.valid,
            "conflictos": validation.errors,
            "base_del_calculo": "Valores USDA por 100 g × gramos de cada ingrediente; estimación sin pérdidas de cocción.",
            **extra,
        }

    def compatible(self, profile: UserProfile | None) -> list[Recipe]:
        return [r for r in self.recipes.values() if validate_recipe(r, self.catalog, profile).valid]

    def _get(self, recipe_id: str) -> Recipe:
        recipe = self.recipes.get(recipe_id.strip())
        if recipe is None:
            found = [
                r
                for r in self.recipes.values()
                if _words(recipe_id)
                and all(any(_same_word(q, w) for w in _words(r.title)) for q in _words(recipe_id))
            ]
            if len(found) == 1:
                return found[0]
            raise LookupError(
                f"No tengo la receta '{recipe_id}'. Usa buscar_recetas para ver las disponibles."
            )
        return recipe

    def _foods_matching(self, text: str) -> set[str]:
        return {f.food_id for f in self.catalog.search(text)}

    # ------------------------------------------------------------ buscar recetas / mi nevera

    def search(
        self,
        profile: UserProfile | None = None,
        *,
        ingredientes: list[str] | None = None,
        comida: str | None = None,
        max_kcal: float | None = None,
        min_proteina: float | None = None,
        tiempo_max: int | None = None,
        texto: str | None = None,
        limite: int = 5,
    ) -> dict:
        available, unknown = set(), []
        for name in ingredientes or []:
            ids = self._foods_matching(name)
            available |= ids
            if not ids:
                unknown.append(name)
        results, excluded = [], 0
        for recipe in self.recipes.values():
            if not validate_recipe(recipe, self.catalog, profile).valid:
                excluded += 1
                continue
            if comida and comida not in recipe.tags:
                continue
            if tiempo_max and (recipe.time_minutes_estimate or 999) > tiempo_max:
                continue
            if texto:
                haystack = _words(
                    recipe.title + " " + " ".join(i.ingredient_name for i in recipe.ingredients)
                )
                if not all(any(_same_word(q, w) for w in haystack) for q in _words(texto)):
                    continue
            per = calculate_nutrition(recipe.ingredients, self.catalog, servings=recipe.servings).per_serving
            if max_kcal and per.kcal > Decimal(str(max_kcal)):
                continue
            if min_proteina and per.protein_g < Decimal(str(min_proteina)):
                continue
            main = [i for i in recipe.ingredients if i.food_id not in PANTRY]
            have = [i.ingredient_name for i in main if i.food_id in available]
            missing = [i.ingredient_name for i in main if i.food_id not in available]
            if ingredientes and not have:
                continue
            results.append(
                {
                    "recipe_id": recipe.recipe_id,
                    "titulo": recipe.title,
                    "kcal": _num(per.kcal, 0),
                    "protein_g": _num(per.protein_g),
                    "tiempo_min": recipe.time_minutes_estimate,
                    "comidas": recipe.tags,
                    "dieta": self.diet_label(recipe),
                    "tienes": have if ingredientes else None,
                    "te_falta": missing if ingredientes else None,
                }
            )
        if ingredientes:
            results.sort(key=lambda r: (-len(r["tienes"]), len(r["te_falta"]), r["recipe_id"]))
        elif min_proteina:
            results.sort(key=lambda r: -r["protein_g"])
        return {
            "tipo": "busqueda",
            "recetas": results[:limite],
            "total_encontradas": len(results),
            "descartadas_por_perfil": excluded,
            "ingredientes_no_reconocidos": unknown,
        }

    # ------------------------------------------------------------ ver / escalar

    def view(
        self,
        profile: UserProfile | None,
        recipe_id: str,
        *,
        raciones: int = 1,
        objetivo_kcal: float | None = None,
    ) -> dict:
        recipe = self._get(recipe_id)
        validation = validate_recipe(recipe, self.catalog, profile)
        if not validation.valid:
            return {
                "error": f"'{recipe.title}' no es compatible con tu perfil.",
                "conflictos": validation.errors,
            }
        note = None
        if objetivo_kcal:
            recipe = adjust_portions(recipe, str(objetivo_kcal), self.catalog, profile=profile)
            note = f"Cantidades multiplicadas por el mismo factor para acercarse a {objetivo_kcal:.0f} kcal por ración."
        if raciones and raciones != 1:
            if not 1 <= raciones <= 12:
                raise ValueError("Puedo preparar entre 1 y 12 raciones")
            recipe = scale_recipe(recipe, raciones)
            recipe.servings = recipe.servings * raciones
        return self.card(recipe, profile, nota=note)

    # ------------------------------------------------------------ sustituir

    def substitute_options(self, profile: UserProfile | None, recipe: Recipe, position: int, limite: int = 4):
        """Alimentos del catálogo cuya energía se reparte de forma parecida entre proteína, hidratos y grasa."""

        def shares(food):
            n = food.nutrients_per_100g
            parts = [n.protein_g * 4, n.carbs_g * 4, n.fat_g * 9]
            total = sum(parts) or Decimal(1)
            return [p / total for p in parts]

        old = recipe.ingredients[position]
        old_food = self.catalog.lookup_food(old.food_id)
        target = shares(old_food)
        old_kcal = old.grams * old_food.nutrients_per_100g.kcal / 100
        in_recipe = {i.food_id for i in recipe.ingredients}
        candidates = []
        for food in self.catalog.foods.values():
            n = food.nutrients_per_100g
            if food.food_id in in_recipe or None in (n.kcal, n.protein_g, n.carbs_g, n.fat_g) or not n.kcal:
                continue
            grams = round_grams(min(max(old_kcal * 100 / n.kcal, Decimal(10)), Decimal(400)))
            data = recipe.model_dump()
            data["ingredients"][position] = RecipeIngredient(
                ingredient_name=food.name_es, food_id=food.food_id, grams=grams, state=food.state
            ).model_dump()
            variant = Recipe.model_validate(data)
            if not validate_recipe(variant, self.catalog, profile).valid:
                continue
            distance = sum(abs(a - b) for a, b in zip(shares(food), target, strict=True))
            candidates.append((distance, food, grams, variant))
        candidates.sort(key=lambda c: (c[0], c[1].food_id))
        return [
            {
                "alimento": food.name_es,
                "gramos": _num(grams, 0),
                "receta_por_racion": _macros(
                    calculate_nutrition(variant.ingredients, self.catalog).per_serving
                ),
            }
            for _, food, grams, variant in candidates[:limite]
        ]

    def substitute(
        self,
        profile: UserProfile | None,
        recipe_id: str,
        ingrediente: str,
        sustituto: str | None = None,
        gramos: float | None = None,
    ) -> dict:
        recipe = self._get(recipe_id)
        words = _words(ingrediente)
        positions = [
            n for n, item in enumerate(recipe.ingredients)
            if words and all(any(_same_word(q, w) for w in _words(item.ingredient_name)) for q in words)
        ]  # fmt: skip
        if len(positions) != 1:
            names = ", ".join(i.ingredient_name for i in recipe.ingredients)
            return {
                "error": f"No encuentro un único '{ingrediente}' en {recipe.title}. Ingredientes: {names}"
            }
        old = recipe.ingredients[positions[0]]
        old_food = self.catalog.lookup_food(old.food_id)
        try:
            if not sustituto:
                raise FoodNotFoundError("Sin sustituto indicado.")
            new_food = self.catalog.resolve(sustituto)
        except (FoodNotFoundError, AmbiguousFoodError) as exc:
            # Gemini no conoce el catálogo: le propongo alternativas que sí existen, ya calculadas.
            return {
                "tipo": "opciones_sustitucion",
                "aviso": str(exc),
                "receta": recipe.title,
                "ingrediente": old.ingredient_name,
                "opciones": self.substitute_options(profile, recipe, positions[0]),
            }
        if gramos:
            grams, rule = Decimal(str(gramos)), "Cantidad indicada por el usuario."
        else:
            # Criterio por defecto: misma energía que el ingrediente original (nunca gramo por gramo).
            old_kcal = old.grams * old_food.nutrients_per_100g.kcal / 100
            grams = old_kcal * 100 / new_food.nutrients_per_100g.kcal
            grams = round_grams(min(max(grams, Decimal(10)), Decimal(400)))
            rule = "Cantidad calculada para aportar aproximadamente la misma energía que el ingrediente original."
        data = recipe.model_dump()
        data["ingredients"][positions[0]] = RecipeIngredient(
            ingredient_name=new_food.name_es, food_id=new_food.food_id, grams=grams, state=new_food.state
        ).model_dump()
        data.update(
            recipe_id=f"{recipe.recipe_id}-var",
            title=f"{recipe.title} (con {new_food.name_es.split(',')[0].lower()})",
        )
        variant = Recipe.model_validate(data)
        before = self.card(recipe, profile)
        after = self.card(variant, profile)
        after["avisos"].append(
            "He cambiado un ingrediente: revisa los pasos, la técnica y el tiempo pueden variar."
        )
        return {
            "tipo": "sustitucion",
            "cambio": {
                "quitar": f"{old.ingredient_name} ({_num(old.grams, 0)} g)",
                "poner": f"{new_food.name_es} ({_num(grams, 0)} g)",
                "criterio": rule,
            },
            "antes_por_racion": before["por_racion"],
            "despues_por_racion": after["por_racion"],
            "receta": after,
        }

    # ------------------------------------------------------------ plato libre

    def dish(
        self,
        profile: UserProfile | None,
        ingredientes: list[dict],
        *,
        raciones: int = 1,
        nombre: str = "Plato de MILO",
    ) -> dict:
        items, problems = [], []
        for entry in ingredientes:
            try:
                food = self.catalog.resolve(str(entry["alimento"]))
            except (FoodNotFoundError, AmbiguousFoodError) as exc:
                problems.append(str(exc))
                continue
            items.append(
                RecipeIngredient(
                    ingredient_name=food.name_es,
                    food_id=food.food_id,
                    grams=Decimal(str(entry["gramos"])),
                    state=food.state,
                )
            )
        if problems:
            return {"error": "No he podido identificar todos los alimentos.", "detalles": problems}
        recipe = Recipe(
            recipe_id="plato", title=nombre, servings=raciones, ingredients=items,
            steps=["Plato propuesto en la conversación."], tags=[],
        )  # fmt: skip
        result = self.card(recipe, profile)
        result["tipo"] = "plato"
        return result

    # ------------------------------------------------------------ plan semanal

    def weekly_plan(
        self,
        profile: UserProfile | None,
        *,
        kcal_diarias: float | None = None,
        dias: int = 7,
        comidas: int = 4,
    ) -> dict:
        target = Decimal(str(kcal_diarias or (profile.daily_kcal if profile else None) or 2000))
        notes = (
            [] if (kcal_diarias or (profile and profile.daily_kcal)) else ["Uso 2000 kcal/día por defecto."]
        )
        if not 1200 <= target <= 4500:
            raise ValueError(
                "Planifico entre 1200 y 4500 kcal diarias; fuera de ese rango consulta a un profesional."
            )
        if not 1 <= dias <= 7 or comidas not in SHARES:
            raise ValueError("Admito de 1 a 7 días y 3 o 4 comidas al día")
        pool = self.compatible(profile)
        groups = {meal: [r for r in pool if meal in r.tags] for meal in SHARES[comidas]}
        if "snack" in groups and not groups["snack"]:
            groups["snack"] = groups["desayuno"]
        if not groups["desayuno"]:
            groups["desayuno"] = groups.get("snack") or []
        empty = [meal for meal, options in groups.items() if not options]
        if empty:
            return {"error": "No tengo recetas compatibles con tu perfil para: " + ", ".join(empty)}
        days, used = [], defaultdict(int)
        for d in range(dias):
            meals, eaten_today = [], set()
            for meal, share in SHARES[comidas].items():
                options = sorted(groups[meal], key=lambda r: (used[r.recipe_id], r.recipe_id))
                # Evito repetir una receta el mismo día y priorizo las menos usadas en la semana.
                recipe = next((r for r in options if r.recipe_id not in eaten_today), options[0])
                eaten_today.add(recipe.recipe_id)
                used[recipe.recipe_id] += 1
                base = calculate_nutrition(recipe.ingredients, self.catalog).per_serving.kcal
                factor = min(max(target * share / base, Decimal("0.5")), Decimal("2.5"))
                scaled = scale_recipe(recipe, factor, rounded=True)
                values = _macros(calculate_nutrition(scaled.ingredients, self.catalog).totals)
                meals.append(
                    {
                        "comida": MEAL_NAMES[meal],
                        "recipe_id": recipe.recipe_id,
                        "titulo": recipe.title,
                        "factor": float(round(factor, 2)),
                        "ingredientes": [
                            {"nombre": i.ingredient_name, "gramos": _num(i.grams, 0), "food_id": i.food_id}
                            for i in scaled.ingredients
                        ],
                        **values,
                    }
                )
            total = {
                k: round(sum(m[k] or 0 for m in meals), 1) for k in ["kcal", "protein_g", "carbs_g", "fat_g"]
            }
            days.append({"dia": DAYS[d], "comidas": meals, "total": total})
        average = {k: round(sum(d["total"][k] for d in days) / len(days), 1) for k in days[0]["total"]}
        deviation = abs(Decimal(str(average["kcal"])) - target) / target
        if deviation > Decimal("0.05"):
            notes.append(
                f"La media ({average['kcal']:.0f} kcal) se aleja más de un 5 % del objetivo: "
                "algunas recetas no admiten escalarse tanto. Puedo añadir un snack o cambiar recetas."
            )
        notes.append(
            "Pesos redondeados a cantidades fáciles de medir; los totales se calculan con esos pesos."
        )
        return {
            "tipo": "plan",
            "kcal_objetivo": float(target),
            "dias": days,
            "media_diaria": average,
            "avisos": notes,
        }

    # ------------------------------------------------------------ lista de la compra

    def shopping_list(self, plan: dict | None = None, recipe_ids: list[str] | None = None) -> dict:
        grams: dict[str, Decimal] = defaultdict(Decimal)
        if plan:
            for day in plan["dias"]:
                for meal in day["comidas"]:
                    for item in meal["ingredientes"]:
                        grams[item["food_id"]] += Decimal(str(item["gramos"]))
        for recipe_id in recipe_ids or []:
            for item in self._get(recipe_id).ingredients:
                grams[item.food_id] += item.grams
        if not grams:
            return {"error": "Primero necesito un menú (plan_semanal) o una lista de recetas."}
        categories: dict[str, list] = defaultdict(list)
        for food_id, amount in grams.items():
            food = self.catalog.lookup_food(food_id)
            name = " " + _normalize_name(food.name_es)
            category = next(
                (title for title, keys in SHOPPING_CATEGORIES if any(" " + k in name for k in keys)),
                "Frutas y verduras",
            )
            categories[category].append(
                {"nombre": food.name_es, "gramos": _num(round_grams(amount), 0), "food_id": food_id}
            )
        order = [title for title, _ in SHOPPING_CATEGORIES] + ["Frutas y verduras"]
        return {
            "tipo": "lista_compra",
            "categorias": [
                {"categoria": title, "items": sorted(categories[title], key=lambda i: i["nombre"])}
                for title in sorted(categories, key=order.index)
            ],
            "total_productos": len(grams),
            "nota": "Cantidades en peso comestible (sin cáscara, piel o hueso). Ajusta al formato de venta.",
        }


def _normalize_name(text: str) -> str:
    return " ".join(_words(text))


# ---------------------------------------------------------------- perfil


def update_profile(
    profile: UserProfile,
    catalog: FoodCatalog,
    *,
    dieta: str | None = None,
    alergias: list[str] | None = None,
    intolerancias: list[str] | None = None,
    no_me_gusta: list[str] | None = None,
    objetivo: str | None = None,
    kcal_diarias: int | None = None,
    preferencias: list[str] | None = None,
) -> tuple[UserProfile, list[str]]:
    """Añade información al perfil. Devuelve el perfil nuevo y avisos de lo que no he podido registrar."""
    data = profile.model_dump()
    restrictions = [DietaryRestriction.model_validate(r) for r in data.pop("restrictions")]
    notes = []
    if dieta:
        key = _normalize_name(dieta)
        restrictions = [r for r in restrictions if r.kind != "diet"]
        if key in DIETS:
            restrictions.append(DietaryRestriction(kind="diet", value=DIETS[key]))
        elif key not in {"ninguna", "omnivora", "normal"}:
            notes.append(f"No sé aplicar la dieta '{dieta}'; solo distingo vegetariana y vegana.")
    for kind, names in [("allergy", alergias or []), ("intolerance", intolerancias or [])]:
        for name in names:
            code = ALLERGEN_INPUT.get(_normalize_name(name)) or ALLERGEN_INPUT.get(
                _normalize_name(name).rstrip("s")
            )
            if code is None:
                notes.append(f"No tengo '{name}' en mi lista de alérgenos; no puedo filtrarlo con seguridad.")
            elif not any(r.kind == kind and r.value == code for r in restrictions):
                restrictions.append(DietaryRestriction(kind=kind, value=code))
    disliked = set(data["disliked_food_ids"])
    for name in no_me_gusta or []:
        ids = {f.food_id for f in catalog.search(name)}
        if ids:
            disliked |= ids
        else:
            notes.append(f"'{name}' no está en mi catálogo, así que ninguna receta lo usa.")
    data.update(
        restrictions=restrictions,
        disliked_food_ids=disliked,
        goal=objetivo or data["goal"],
        daily_kcal=kcal_diarias or data["daily_kcal"],
        preferences=sorted(set(data["preferences"]) | set(preferencias or [])),
    )
    return UserProfile.model_validate(data), notes


def describe_profile(profile: UserProfile, catalog: FoodCatalog) -> str:
    """Resumen legible del perfil para el system prompt y la app."""
    parts = []
    diet = [r.value for r in profile.restrictions if r.kind == "diet"]
    if diet:
        parts.append("dieta " + {"vegetarian": "vegetariana", "vegan": "vegana"}[diet[0]])
    for kind, label in [("allergy", "alergia a"), ("intolerance", "intolerancia a")]:
        values = [ALLERGENS_ES[r.value] for r in profile.restrictions if r.kind == kind]
        if values:
            parts.append(f"{label} " + ", ".join(values))
    if profile.disliked_food_ids:
        names = sorted(
            {catalog.foods[i].name_es.split(",")[0] for i in profile.disliked_food_ids if i in catalog.foods}
        )
        parts.append("no le gusta: " + ", ".join(names))
    if profile.goal:
        parts.append("objetivo: " + profile.goal)
    if profile.daily_kcal:
        parts.append(f"unas {profile.daily_kcal} kcal al día")
    if profile.preferences:
        parts.append("preferencias: " + ", ".join(profile.preferences))
    return "; ".join(parts) or "sin datos registrados"
