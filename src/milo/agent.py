"""Grafo pequeño: interpretar → recuperar → calcular/validar → responder."""

from __future__ import annotations

import json
import re
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from milo.catalog import FoodCatalog
from milo.config import ROOT
from milo.models import Recipe, UserProfile
from milo.nutrition import adjust_portions, calculate_recipe_nutrition, validate_recipe
from milo.rag import NutritionRAG, RagAnswer, show_answer


class TurnPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["general", "recipe", "nutrition", "adjust", "clarify"]
    query: str = Field(min_length=1, description="Pregunta completa, resolviendo referencias al historial")
    recipe_id: str | None = None
    target_kcal: float | None = Field(default=None, gt=0)
    clarification: str = ""


class AgentState(MessagesState):
    profile: dict
    plan: dict
    fragments: list[dict]
    tool_result: dict | None
    blocked: str
    last_recipe_id: str | None
    last_recipe: dict | None
    answer: str


def render_recipe(recipe: Recipe, nutrition: dict) -> str:
    """Los pesos y macros que muestro salen del código, sin reescritura del modelo."""
    lines = [f"**{recipe.title} ({recipe.recipe_id})** — {recipe.servings} ración(es).", "", "Ingredientes:"]
    for item in recipe.ingredients:
        lines.append(f"- {item.ingredient_name}: {item.grams:.2f} g ({item.state}).")
    if recipe.review_status == "verified":
        lines.extend(["", "Preparación:"])
        lines.extend(f"{i}. {step}" for i, step in enumerate(recipe.steps, 1))
    lines.extend(["", "Cálculo Python aproximado por ración:", ""])
    labels = {
        "kcal": "Energía (kcal)",
        "protein_g": "Proteína (g)",
        "carbs_g": "Hidratos (g)",
        "fat_g": "Grasa (g)",
        "fiber_g": "Fibra (g)",
    }
    lines.extend(
        f"- {labels[key]}: {value if value is not None else 'desconocido'}"
        for key, value in nutrition["per_serving"].items()
    )
    lines.extend(["", nutrition["basis"], "Los alérgenos conocidos no garantizan ausencia de trazas."])
    if recipe.review_status != "verified":
        lines.append("El escalado supera la validación numérica; su adaptación culinaria queda pendiente.")
        lines.append(
            "Muestro los pesos redondeados; calculo con precisión completa. Si redondeo al cocinar, recalculo."
        )
    return "\n".join(lines)


class MiloAgent:
    def __init__(self, rag: NutritionRAG | None = None):
        self.rag = rag or NutritionRAG()
        self.catalog = FoodCatalog.from_csv(ROOT / "data/structured/foods.csv")
        self.recipes = {
            r["recipe_id"]: Recipe.model_validate(r)
            for r in json.loads((ROOT / "data/structured/recipes.json").read_text(encoding="utf-8"))
        }
        self.planner = self.rag.model.with_structured_output(TurnPlan)
        graph = StateGraph(AgentState)
        for name, function in [
            ("interpretar", self.interpret),
            ("recuperar", self.retrieve),
            ("herramientas", self.calculate),
            ("responder", self.respond),
        ]:
            graph.add_node(name, function)
        graph.add_edge(START, "interpretar")
        graph.add_edge("interpretar", "recuperar")
        graph.add_edge("recuperar", "herramientas")
        graph.add_edge("herramientas", "responder")
        graph.add_edge("responder", END)
        # Memoria por hilo durante la vida de este objeto; no persiste tras reiniciar Python.
        self.graph = graph.compile(checkpointer=InMemorySaver())

    def interpret(self, state: AgentState) -> dict:
        recipes = [
            {"id": r.recipe_id, "title": r.title, "status": r.review_status} for r in self.recipes.values()
        ]
        prompt = f"""Organiza la consulta para MILO; no respondas ni calcules nutrientes.
Usa general para conocimiento documental; recipe para recomendar/preparar; nutrition para macros;
adjust solo para escalar uniformemente a kcal por ración, nunca para sustituir ingredientes.
Elige recipe_id únicamente del catálogo. Si 'esa receta' se refiere al turno anterior, conserva su ID.
No elijas una receta arbitraria si falta contexto: usa clarify y pide aclaración.
El perfil es explícito y lo comprueba Python. No lo modifiques. Si el usuario declara una NUEVA
alergia o dieta personal no registrada, usa clarify y pide registrarla en UserProfile antes de recomendar.
Las preguntas educativas sobre alergias pueden ser general. No conviertas un rechazo anterior en éxito.
Si piden cambios de ingredientes, explica mediante general los límites del documento; no inventes recetas.
Catálogo: {json.dumps(recipes, ensure_ascii=False)}
Perfil: {json.dumps(state["profile"], ensure_ascii=False)}
Última receta validada: {state.get("last_recipe_id")}
"""
        plan = self.planner.invoke([SystemMessage(content=prompt), *state["messages"][-8:]])
        return {"plan": plan.model_dump(), "fragments": [], "tool_result": None, "blocked": ""}

    def retrieve(self, state: AgentState) -> dict:
        plan = TurnPlan.model_validate(state["plan"])
        if plan.action == "clarify":
            return {"blocked": plan.clarification or "Necesito una receta concreta o registrar tu perfil."}
        recipe = self.recipes.get(plan.recipe_id)
        query = f"{recipe.recipe_id} {recipe.title}" if recipe and plan.action != "general" else plan.query
        fragments = self.rag.retrieve(query, k=6)
        profile = UserProfile.model_validate(state["profile"])
        selected = []
        for fragment in fragments:
            if fragment["metadata"]["source_id"] == "MILO_RECETAS":
                match = re.match(r"(r\d{3})\b", fragment["metadata"].get("section", ""))
                candidate = self.recipes.get(match[1]) if match else None
                if candidate is None or not validate_recipe(candidate, self.catalog, profile).valid:
                    continue
                if plan.action != "general" and candidate.recipe_id != plan.recipe_id:
                    continue
            elif plan.action != "general":
                continue
            selected.append({**fragment, "citation": len(selected) + 1})
        return {"fragments": selected}

    def calculate(self, state: AgentState) -> dict:
        plan = TurnPlan.model_validate(state["plan"])
        if state["blocked"] or plan.action in {"general", "clarify"}:
            return {}
        recipe = self.recipes.get(plan.recipe_id)
        if recipe is None or recipe.review_status != "verified":
            return {"blocked": "No dispongo de esa receta revisada. Indica una receta del corpus disponible."}
        if (
            plan.action == "nutrition"
            and state.get("last_recipe_id") == plan.recipe_id
            and state.get("last_recipe")
        ):
            recipe = Recipe.model_validate(state["last_recipe"])
        profile = UserProfile.model_validate(state["profile"])
        validation = validate_recipe(recipe, self.catalog, profile)
        if not validation.valid:
            return {
                "blocked": "No puedo recomendar esta receta con el perfil registrado: "
                + "; ".join(validation.errors)
            }
        if not state["fragments"]:
            return {
                "blocked": "No he recuperado el documento de esa receta; no completaré sus datos por intuición."
            }
        try:
            if plan.action == "adjust":
                if plan.target_kcal is None:
                    return {"blocked": "Indica el objetivo de kcal por ración para el escalado uniforme."}
                recipe = adjust_portions(recipe, str(plan.target_kcal), self.catalog, profile=profile)
            nutrition = calculate_recipe_nutrition(recipe, self.catalog)
        except ValueError as exc:
            return {"blocked": str(exc)}
        result = {
            "recipe": recipe.model_dump(mode="json"),
            "per_serving": nutrition.per_serving.rounded(),
            "totals": nutrition.totals.rounded(),
            "basis": nutrition.basis,
            "validation": validation.model_dump(mode="json"),
        }
        return {"tool_result": result, "last_recipe_id": recipe.recipe_id, "last_recipe": result["recipe"]}

    def respond(self, state: AgentState) -> dict:
        if state["blocked"]:
            answer = state["blocked"]
        elif state["tool_result"]:
            result = state["tool_result"]
            recipe = Recipe.model_validate(result["recipe"])
            introduction = self.rag.generate(
                "Explica en una sola frase la técnica culinaria principal de esta receta. "
                "No añadas ingredientes, cantidades ni macros; la ficha calculada se muestra a continuación.",
                state["fragments"],
            )
            answer = introduction + "\n\n" + render_recipe(recipe, result)
        else:
            answer = self.rag.generate(
                state["plan"]["query"],
                state["fragments"],
                extra_context="Perfil registrado: " + json.dumps(state["profile"], ensure_ascii=False),
            )
        return {"answer": answer, "messages": [AIMessage(content=answer)]}

    def ask(self, question: str, *, thread_id: str, profile: UserProfile | None = None) -> dict:
        if not question.strip() or not thread_id.strip():
            raise ValueError("La pregunta y el identificador de conversación son obligatorios")
        config = {"configurable": {"thread_id": thread_id}}
        previous = self.graph.get_state(config).values
        if profile and previous and previous["profile"]["user_id"] != profile.user_id:
            raise ValueError("Usa un hilo distinto para otro usuario")
        update = {"messages": [HumanMessage(content=question)]}
        if profile is not None or not previous:
            update["profile"] = (profile or UserProfile(user_id=thread_id)).model_dump(mode="json")
        return self.graph.invoke(update, config=config)


def show_turn(state: dict) -> None:
    question = next(m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage))
    print("Ruta:", state["plan"]["action"], "| Herramienta calculada:", state["tool_result"] is not None)
    show_answer(RagAnswer(question, state["fragments"], state["answer"]), label="RESPUESTA DEL AGENTE")
