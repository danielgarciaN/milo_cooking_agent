"""Herramientas de cocina con el catálogo y el recetario reales. No llaman a Gemini."""

import pytest

from milo.models import DietaryRestriction, UserProfile
from milo.recipes import Kitchen, describe_profile, update_profile


@pytest.fixture(scope="module")
def kitchen():
    return Kitchen()


def test_fridge_search_reports_what_is_missing(kitchen):
    result = kitchen.search(UserProfile(), ingredientes=["pollo", "arroz", "aguacate", "huevos"])
    top = result["recetas"][0]
    assert top["recipe_id"] == "r001"
    assert top["te_falta"] == ["Tomate roma, crudo"]
    assert result["ingredientes_no_reconocidos"] == []
    assert kitchen.search(UserProfile(), ingredientes=["chocolate"])["ingredientes_no_reconocidos"] == [
        "chocolate"
    ]


def test_profile_filters_recipes(kitchen):
    profile, notes = update_profile(
        UserProfile(), kitchen.catalog, dieta="vegetariano", no_me_gusta=["tomate"]
    )
    assert notes == []
    assert "dieta vegetariana" in describe_profile(profile, kitchen.catalog)
    found = kitchen.search(profile, limite=50)["recetas"]
    assert found and all(r["dieta"] in {"vegetariana", "vegana"} for r in found)
    assert not any("tomate" in r["titulo"].lower() for r in found)
    assert "error" in kitchen.view(profile, "r001")


def test_unknown_allergen_is_reported_not_ignored(kitchen):
    profile, notes = update_profile(UserProfile(), kitchen.catalog, alergias=["kiwi exótico"])
    assert notes and profile.restrictions == []


def test_view_scales_to_target_kcal(kitchen):
    card = kitchen.view(UserProfile(), "r001", objetivo_kcal=700)
    assert card["por_racion"]["kcal"] == 700
    doubled = kitchen.view(UserProfile(), "r001", raciones=2)
    assert doubled["raciones"] == 2
    assert doubled["total"]["kcal"] == pytest.approx(2 * doubled["por_racion"]["kcal"], abs=1)


def test_substitution_keeps_energy_and_recalculates(kitchen):
    result = kitchen.substitute(UserProfile(), "r001", "arroz", "patata")
    assert "Patata" in result["cambio"]["poner"]
    assert abs(result["despues_por_racion"]["kcal"] - result["antes_por_racion"]["kcal"]) < 15
    assert result["receta"]["recipe_id"] == "r001-var"


def test_dish_requires_known_foods(kitchen):
    ok = kitchen.dish(
        UserProfile(), [{"alimento": "huevo", "gramos": 120}, {"alimento": "espinacas", "gramos": 80}]
    )
    assert ok["por_racion"]["kcal"] > 0
    assert "error" in kitchen.dish(UserProfile(), [{"alimento": "chocolate", "gramos": 50}])


def test_weekly_plan_and_shopping_list(kitchen):
    plan = kitchen.weekly_plan(UserProfile(), kcal_diarias=2500, dias=7)
    assert len(plan["dias"]) == 7 and len(plan["dias"][0]["comidas"]) == 4
    assert abs(plan["media_diaria"]["kcal"] - 2500) / 2500 < 0.05
    for day in plan["dias"]:
        ids = [m["recipe_id"] for m in day["comidas"]]
        assert len(ids) == len(set(ids))
        assert day["total"]["kcal"] == pytest.approx(sum(m["kcal"] for m in day["comidas"]), abs=0.5)
    shopping = kitchen.shopping_list(plan)
    names = [c["categoria"] for c in shopping["categorias"]]
    assert "Frutas y verduras" in names and shopping["total_productos"] > 10
    with pytest.raises(ValueError):
        kitchen.weekly_plan(UserProfile(), kcal_diarias=800)


def test_plan_respects_allergies(kitchen):
    profile = UserProfile(restrictions=[DietaryRestriction(kind="allergy", value="milk")])
    plan = kitchen.weekly_plan(profile, kcal_diarias=2000, dias=3)
    used = {i["food_id"] for d in plan["dias"] for m in d["comidas"] for i in m["ingredientes"]}
    assert not any("milk" in kitchen.catalog.foods[f].allergens for f in used)


def test_substitution_without_known_substitute_offers_catalog_options(kitchen):
    result = kitchen.substitute(UserProfile(), "r007", "aguacate", "hummus")
    assert result["tipo"] == "opciones_sustitucion" and len(result["opciones"]) == 4
    assert all(kitchen.catalog.search(o["alimento"]) for o in result["opciones"])
    allergic = UserProfile(restrictions=[DietaryRestriction(kind="allergy", value="tree_nuts")])
    options = kitchen.substitute(allergic, "r002", "espinaca")["opciones"]
    assert not any("Nuez" in o["alimento"] or "Almendra" in o["alimento"] for o in options)
