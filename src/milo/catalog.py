from __future__ import annotations

import csv
import json
from pathlib import Path

from milo.models import Food


class FoodNotFoundError(LookupError):
    pass


class AmbiguousFoodError(LookupError):
    pass


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
            raise AmbiguousFoodError(f"Especifica un food_id y estado para {query!r}")
        return matches[0]


def lookup_food(query: str, catalog: FoodCatalog, *, state: str | None = None) -> Food:
    return catalog.lookup_food(query, state=state)
