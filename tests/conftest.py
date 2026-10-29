from pathlib import Path

import pytest

from milo.models import Food, NutrientValues, Recipe, RecipeIngredient
from milo.repositories.catalog import FoodCatalog

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalog():
    """Datos sintéticos exclusivos de tests; nunca se exportan al catálogo real."""
    base = {
        "name_source": "Synthetic test food",
        "source_id": "TEST_ONLY",
        "source_version": "1",
        "review_status": "verified",
        "allergen_review_complete": True,
        "vegan": True,
        "vegetarian": True,
    }
    return FoodCatalog(
        [
            Food(
                food_id="a",
                name_es="Alimento A",
                state="raw",
                nutrients_per_100g=NutrientValues(kcal=100, protein_g=10, carbs_g=15, fat_g=2, fiber_g=3),
                **base,
            ),
            Food(
                food_id="b",
                name_es="Alimento B",
                state="raw",
                nutrients_per_100g=NutrientValues(kcal=200, protein_g=20, carbs_g=25, fat_g=4, fiber_g=6),
                **base,
            ),
            Food(
                food_id="cooked",
                name_es="Alimento A",
                state="cooked",
                nutrients_per_100g=NutrientValues(kcal=300, protein_g=30, carbs_g=45, fat_g=6, fiber_g=9),
                **base,
            ),
        ]
    )


@pytest.fixture
def recipe():
    return Recipe(
        recipe_id="test",
        title="Receta de prueba sintética",
        servings=2,
        ingredients=[
            RecipeIngredient(ingredient_name="A", food_id="a", grams=100, state="raw"),
            RecipeIngredient(ingredient_name="B", food_id="b", grams=50, state="raw"),
        ],
        steps=["Ejemplo matemático; no receta real."],
    )


@pytest.fixture(scope="session")
def real_catalog():
    return FoodCatalog.from_csv(ROOT / "data/structured/foods.csv")
