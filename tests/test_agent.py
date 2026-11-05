from types import SimpleNamespace

import pytest

from milo.agent import MiloAgent, TurnPlan
from milo.models import DietaryRestriction, UserProfile
from milo.rag import load_documents


class UnitRag:
    """Doble solo para comprobar controles Python; las pruebas live usan Gemini."""

    def __init__(self, plans):
        self.plans = iter(plans)
        self.model = SimpleNamespace(with_structured_output=lambda _: self)
        self.generated = 0
        self.chunks = [c for c in load_documents() if c.source_id == "MILO_RECETAS"]

    def invoke(self, _):
        return next(self.plans)

    def retrieve(self, query, k=6):
        return [
            {"citation": i, "text": c.text, "metadata": c.model_dump(exclude={"text", "chunk_id"})}
            for i, c in enumerate(self.chunks, 1)
        ]

    def generate(self, question, fragments, **kwargs):
        self.generated += 1
        return "Texto de unidad; no es una respuesta real de Gemini [1]."


@pytest.mark.parametrize(
    "recipe_id,kind,value",
    [
        ("r001", "diet", "vegetarian"),
        ("r002", "allergy", "egg"),
        ("r012", "allergy", "milk"),
    ],
)
def test_python_blocks_recipe_even_when_model_selects_it(recipe_id, kind, value):
    rag = UnitRag([TurnPlan(action="recipe", query="Prueba", recipe_id=recipe_id)])
    agent = MiloAgent(rag)
    profile = UserProfile(user_id="test", restrictions=[DietaryRestriction(kind=kind, value=value)])
    result = agent.ask("Prueba", thread_id="test", profile=profile)
    assert result["blocked"] and result["tool_result"] is None
    assert rag.generated == 0


@pytest.mark.parametrize("recipe_id", ["r004", "r999", None])
def test_pending_unknown_and_missing_recipe_cannot_be_calculated(recipe_id):
    rag = UnitRag([TurnPlan(action="nutrition", query="Prueba", recipe_id=recipe_id)])
    result = MiloAgent(rag).ask("Prueba", thread_id="test")
    assert result["blocked"] and result["tool_result"] is None
    assert rag.generated == 0


def test_memory_keeps_adjustment_and_isolates_profiles():
    rag = UnitRag(
        [
            TurnPlan(action="adjust", query="Prueba", recipe_id="r001", target_kcal=600),
            TurnPlan(action="nutrition", query="Prueba", recipe_id="r001"),
            TurnPlan(action="general", query="Prueba"),
        ]
    )
    agent = MiloAgent(rag)
    first = agent.ask("Prueba", thread_id="one", profile=UserProfile(user_id="one", preferences=["arroz"]))
    followup = agent.ask("¿Y ahora?", thread_id="one")
    other = agent.ask("Prueba", thread_id="two")
    assert first["tool_result"]["per_serving"]["kcal"] == "600.00"
    assert followup["tool_result"]["per_serving"] == first["tool_result"]["per_serving"]
    assert followup["profile"]["preferences"] == ["arroz"]
    assert len(followup["messages"]) == 4 and len(other["messages"]) == 2
    assert other["profile"]["preferences"] == [] and other["tool_result"] is None
    with pytest.raises(ValueError, match="otro usuario"):
        agent.ask("Prueba", thread_id="one", profile=UserProfile(user_id="different"))


@pytest.mark.live
def test_real_agent_remembers_recipe_and_calculates():
    agent = MiloAgent()
    first = agent.ask("Recomiéndame una receta sencilla con pollo y arroz.", thread_id="live-memory")
    second = agent.ask("¿Cuántas calorías y proteínas tiene esa receta?", thread_id="live-memory")
    assert first["last_recipe_id"] == second["last_recipe_id"] == "r001"
    assert second["plan"]["action"] == "nutrition"
    assert second["tool_result"]["per_serving"] == first["tool_result"]["per_serving"]
    assert len(second["messages"]) == 4
