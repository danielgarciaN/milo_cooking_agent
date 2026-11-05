"""Contratos de dominio. Un valor desconocido nunca se transforma en cero."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_serializer, model_validator


def reject_bool(value):
    if isinstance(value, bool):
        raise ValueError("Un booleano no es una cantidad")  # noqa: TRY004 - Pydantic recoge ValueError.
    return value


NonNegative = Annotated[Decimal, BeforeValidator(reject_bool), Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[Decimal, BeforeValidator(reject_bool), Field(gt=0, allow_inf_nan=False)]
Text = Annotated[str, Field(min_length=1)]
PreparationState = Literal["raw", "dry", "cooked", "drained", "ready_to_eat", "unknown"]
ReviewStatus = Literal["pending", "verified", "rejected"]
Allergen = Literal[
    "milk",
    "egg",
    "fish",
    "crustacean",
    "mollusc",
    "soy",
    "wheat",
    "gluten",
    "peanut",
    "tree_nuts",
    "sesame",
    "celery",
    "mustard",
    "lupin",
    "sulphites",
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)

    @field_serializer("allergens", "disliked_food_ids", check_fields=False)
    def serialize_sets(self, value):
        return sorted(value)


class NutrientValues(Contract):
    kcal: NonNegative | None = None
    protein_g: NonNegative | None = None
    carbs_g: NonNegative | None = None
    fat_g: NonNegative | None = None
    fiber_g: NonNegative | None = None

    def rounded(self, places: int = 2) -> dict[str, str | None]:
        if isinstance(places, bool) or not isinstance(places, int) or not 0 <= places <= 6:
            raise ValueError("Decimales permitidos: 0 a 6")
        quantum = Decimal(1).scaleb(-places)
        return {
            key: str(value.quantize(quantum, rounding=ROUND_HALF_UP)) if value is not None else None
            for key, value in self.model_dump().items()
        }


class Food(Contract):
    food_id: Text
    name_es: Text
    name_source: Text
    fdc_id: Annotated[int, Field(strict=True, gt=0)] | None = None
    state: PreparationState
    nutrients_per_100g: NutrientValues
    source_id: Text
    source_version: Text
    review_status: ReviewStatus = "pending"
    nutrient_ids: dict[str, int] = Field(default_factory=dict)
    nutrient_record_ids: dict[str, int] = Field(default_factory=dict)
    allergens: set[Allergen] = Field(default_factory=set)
    allergen_review_complete: bool = False
    is_compound: bool = False
    vegan: bool | None = None
    vegetarian: bool | None = None
    notes: str = ""


class RecipeIngredient(Contract):
    ingredient_name: Text
    food_id: Text | None = None
    grams: Positive
    unit: Literal["g"] = "g"
    state: PreparationState
    notes: str = ""


class Recipe(Contract):
    recipe_id: Text
    title: Text
    servings: Annotated[int, Field(strict=True, gt=0)]
    ingredients: Annotated[list[RecipeIngredient], Field(min_length=1)]
    steps: Annotated[list[Text], Field(min_length=1)]
    time_minutes_estimate: Annotated[int, Field(strict=True, gt=0)] | None = None
    difficulty: Literal["fácil", "media"] = "fácil"
    # Tipo de comida: desayuno, comida, cena o snack. Lo uso para buscar recetas y organizar el menú.
    tags: list[str] = Field(default_factory=list)
    allergens: set[Allergen] = Field(default_factory=set)
    review_status: ReviewStatus = "pending"
    notes: list[str] = Field(default_factory=list)


class DietaryRestriction(Contract):
    kind: Literal["allergy", "intolerance", "diet", "exclude_food"]
    value: Text

    @model_validator(mode="after")
    def validate_value(self):
        from typing import get_args

        if self.kind in {"allergy", "intolerance"} and self.value not in get_args(Allergen):
            raise ValueError("Alérgeno no soportado: no se ignora silenciosamente")
        if self.kind == "diet" and self.value not in {"vegan", "vegetarian"}:
            raise ValueError("Dieta no soportada: utiliza vegan o vegetarian")
        return self


class UserProfile(Contract):
    user_id: Text = "usuario"
    goal: str | None = None
    daily_kcal: Annotated[int, Field(gt=0, le=6000)] | None = None
    restrictions: list[DietaryRestriction] = Field(default_factory=list)
    disliked_food_ids: set[str] = Field(default_factory=set)
    preferences: list[str] = Field(default_factory=list)


class ValidationResult(Contract):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    allergens: set[Allergen] = Field(default_factory=set)


class NutritionResult(Contract):
    totals: NutrientValues
    per_serving: NutrientValues
    servings: Annotated[int, Field(strict=True, gt=0)]
    complete: bool
    approximate: bool = True
    missing: dict[str, list[str]] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    food_ids: list[str] = Field(default_factory=list)
    basis: str = "Suma de pesos comestibles de entrada; sin factores de retención o rendimiento de cocción."


class DataSource(Contract):
    source_id: Text
    title: Text
    url: Text
    file_type: Literal["pdf", "zip", "web", "json", "markdown"]
    version: str | None = None
    status: Literal["pending", "downloaded", "provided_local", "failed", "incomplete_archive", "created"]
    downloaded_at: str | None = None
    size_bytes: Annotated[int, Field(ge=0)] | None = None
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None = None
    path: str | None = None
    usage_conditions: Text
    usage: Text
    # Páginas de un PDF que no indexo porque no aportan contenido (portada, índice, contraportada).
    skip_pages: list[int] = Field(default_factory=list)
    download_attempts: list[dict] = Field(default_factory=list)


class DocumentChunk(Contract):
    chunk_id: Text
    text: Text
    source_id: Text
    source_url: Text
    source_sha256: Text
    page: Annotated[int, Field(gt=0)] | None
    section: Text
    version: str | None = None
    usage: Text
