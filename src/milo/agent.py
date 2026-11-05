"""Agente MILO con LangGraph.

    START → recuperar → milo ⇄ herramientas → END

1. recuperar:    busca en ChromaDB los fragmentos de mis documentos relacionados con la pregunta (RAG).
2. milo:         Gemini recibe el system prompt, el perfil, los fragmentos y el historial. Responde o
                 decide llamar a una herramienta.
3. herramientas: ejecuta en Python la herramienta pedida (recetas, macros, menú...) y devuelve el
                 resultado a Gemini, que vuelve al nodo milo para redactar la respuesta.

La memoria es un checkpointer de LangGraph sobre SQLite (storage/memoria.sqlite): cada conversación
tiene un thread_id y su historial, perfil y fragmentos se guardan después de cada paso.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import InjectedState, ToolNode, tools_condition
from langgraph.types import Command
from pydantic import BaseModel, Field

from milo.config import Settings
from milo.models import UserProfile
from milo.rag import NutritionRAG, RagAnswer, create_model, format_context, message_text, show_answer
from milo.recipes import Kitchen, describe_profile, update_profile

MEMORY_TURNS = 8  # Turnos del usuario que envío a Gemini en cada llamada (el resto sigue guardado).


class MiloState(MessagesState):
    """Lo que LangGraph guarda de cada conversación."""

    profile: dict  # Perfil del usuario (dieta, alergias, objetivo...).
    fragments: list[dict]  # Fragmentos recuperados de ChromaDB en el turno actual.


class Ingrediente(BaseModel):
    alimento: str = Field(
        description="Nombre del alimento en español, p. ej. 'pechuga de pollo' o 'arroz blanco'"
    )
    gramos: float = Field(gt=0, le=2000, description="Peso en gramos de la parte comestible")


def _content(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------- herramientas


def make_tools(kitchen: Kitchen, rag: NutritionRAG) -> list:
    """Las herramientas que Gemini puede llamar. Su docstring es la descripción que lee el modelo."""

    def profile_of(state_profile: dict | None) -> UserProfile:
        return UserProfile.model_validate(state_profile or {})

    @tool(response_format="content_and_artifact")
    def buscar_recetas(
        profile: Annotated[dict, InjectedState("profile")],
        ingredientes: list[str] | None = None,
        comida: Literal["desayuno", "comida", "cena", "snack"] | None = None,
        max_kcal: float | None = None,
        min_proteina: float | None = None,
        tiempo_max: int | None = None,
        texto: str | None = None,
    ):
        """Busca recetas del recetario de MILO compatibles con el perfil del usuario.
        Usa `ingredientes` con lo que el usuario tiene en la nevera: indica qué tiene y qué le falta.
        Filtros opcionales: tipo de comida, kcal máximas por ración, proteína mínima (g), minutos máximos
        y texto libre (p. ej. 'garbanzos' o 'salmón')."""
        result = kitchen.search(
            profile_of(profile), ingredientes=ingredientes, comida=comida, max_kcal=max_kcal,
            min_proteina=min_proteina, tiempo_max=tiempo_max, texto=texto,
        )  # fmt: skip
        return _content(result), result

    @tool(response_format="content_and_artifact")
    def ver_receta(
        recipe_id: str,
        profile: Annotated[dict, InjectedState("profile")],
        raciones: int = 1,
        objetivo_kcal: float | None = None,
    ):
        """Devuelve la ficha completa de una receta (ingredientes en gramos, pasos, calorías y macros
        calculados con Python). `raciones` multiplica las cantidades. `objetivo_kcal` escala la receta
        para acercarla a esas kcal por ración (entre la mitad y el doble de la receta original)."""
        result = kitchen.view(profile_of(profile), recipe_id, raciones=raciones, objetivo_kcal=objetivo_kcal)
        return _content(result), result

    @tool(response_format="content_and_artifact")
    def sustituir_ingrediente(
        recipe_id: str,
        ingrediente: str,
        profile: Annotated[dict, InjectedState("profile")],
        sustituto: str | None = None,
        gramos: float | None = None,
    ):
        """Cambia un ingrediente de una receta por otro alimento del catálogo y recalcula los macros.
        Si el usuario no dice por qué cambiarlo, deja `sustituto` vacío: devuelve opciones del catálogo ya
        calculadas. Si no se indican `gramos`, usa la cantidad con energía parecida (nunca gramo por gramo)."""
        result = kitchen.substitute(profile_of(profile), recipe_id, ingrediente, sustituto, gramos)
        return _content(result), result

    @tool(response_format="content_and_artifact")
    def calcular_plato(
        ingredientes: list[Ingrediente],
        profile: Annotated[dict, InjectedState("profile")],
        raciones: int = 1,
        nombre: str = "Plato de MILO",
    ):
        """Calcula calorías y macros de un plato libre a partir de alimentos y gramos. Úsalo para
        propuestas que no están en el recetario o para ajustar cantidades a un objetivo de kcal."""
        items = [i.model_dump() if isinstance(i, BaseModel) else i for i in ingredientes]
        result = kitchen.dish(profile_of(profile), items, raciones=raciones, nombre=nombre)
        return _content(result), result

    @tool(response_format="content_and_artifact")
    def plan_semanal(
        profile: Annotated[dict, InjectedState("profile")],
        kcal_diarias: float | None = None,
        dias: int = 7,
        comidas_por_dia: int = 4,
    ):
        """Crea un menú de 1 a 7 días (3 comidas, o 4 con snack) con recetas compatibles
        con el perfil, escaladas para acercarse a las kcal diarias. Devuelve totales diarios calculados."""
        result = kitchen.weekly_plan(
            profile_of(profile), kcal_diarias=kcal_diarias, dias=dias, comidas=comidas_por_dia
        )
        if "error" in result:
            return _content(result), result
        summary = {
            "kcal_objetivo": result["kcal_objetivo"],
            "media_diaria": result["media_diaria"],
            "dias": [
                {"dia": d["dia"], "total_kcal": d["total"]["kcal"],
                 "comidas": [f"{m['comida']}: {m['titulo']} ({m['kcal']:.0f} kcal)" for m in d["comidas"]]}
                for d in result["dias"]
            ],
            "avisos": result["avisos"],
            "nota": "La app muestra el detalle de cantidades de cada comida.",
        }  # fmt: skip
        return _content(summary), result

    @tool(response_format="content_and_artifact")
    def lista_compra(
        messages: Annotated[list, InjectedState("messages")],
        recetas: list[str] | None = None,
    ):
        """Genera la lista de la compra agrupada por categorías. Sin argumentos usa el último menú
        creado en esta conversación; con `recetas` (IDs) suma los ingredientes de esas recetas."""
        plan = None
        if not recetas:
            for message in reversed(messages):
                if isinstance(message, ToolMessage) and message.name == "plan_semanal" and message.artifact:
                    plan = message.artifact
                    break
        result = kitchen.shopping_list(plan=plan, recipe_ids=recetas)
        return _content(result), result

    @tool
    def guardar_perfil(
        profile: Annotated[dict, InjectedState("profile")],
        tool_call_id: Annotated[str, InjectedToolCallId],
        dieta: Literal["vegetariana", "vegana", "ninguna"] | None = None,
        alergias: list[str] | None = None,
        intolerancias: list[str] | None = None,
        no_me_gusta: list[str] | None = None,
        objetivo: str | None = None,
        kcal_diarias: int | None = None,
        preferencias: list[str] | None = None,
    ):
        """Guarda en la memoria del usuario su dieta, alergias, intolerancias, alimentos que no le gustan,
        objetivo, kcal diarias o preferencias. Las recetas incompatibles se filtran después automáticamente."""
        new, notes = update_profile(
            profile_of(profile), kitchen.catalog, dieta=dieta, alergias=alergias, intolerancias=intolerancias,
            no_me_gusta=no_me_gusta, objetivo=objetivo, kcal_diarias=kcal_diarias, preferencias=preferencias,
        )  # fmt: skip
        summary = {
            "tipo": "perfil",
            "perfil_guardado": describe_profile(new, kitchen.catalog),
            "avisos": notes,
        }
        message = ToolMessage(
            _content(summary), tool_call_id=tool_call_id, name="guardar_perfil", artifact=summary
        )
        return Command(update={"profile": new.model_dump(mode="json"), "messages": [message]})

    @tool
    def buscar_documentos(
        consulta: str,
        fragments: Annotated[list, InjectedState("fragments")],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        """Busca más información en los documentos de MILO (guía AESAN, recetario, técnicas y sustituciones)
        cuando los fragmentos recibidos no bastan. Escribe una consulta concreta."""
        start = len(fragments or [])
        found = [{**f, "citation": start + f["citation"]} for f in rag.retrieve(consulta, k=3)]
        message = ToolMessage(format_context(found), tool_call_id=tool_call_id, name="buscar_documentos")
        return Command(update={"fragments": [*(fragments or []), *found], "messages": [message]})

    return [
        buscar_recetas, ver_receta, sustituir_ingrediente, calcular_plato,
        plan_semanal, lista_compra, guardar_perfil, buscar_documentos,
    ]  # fmt: skip


# ---------------------------------------------------------------- el grafo


def recent_history(messages: list, turns: int = MEMORY_TURNS) -> list:
    """Últimos turnos completos; siempre empiezo en un mensaje del usuario para no partir una llamada a herramienta."""
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    return messages[starts[-turns] if len(starts) >= turns else 0 :]


class MiloAgent:
    def __init__(
        self, rag: NutritionRAG | None = None, kitchen: Kitchen | None = None, *, memory_path=None, model=None
    ):
        self.rag = rag or NutritionRAG()
        self.kitchen = kitchen or Kitchen()
        self.tools = make_tools(self.kitchen, self.rag)
        # Gemini con las herramientas "atadas": puede responder o pedir que se ejecute una de ellas.
        self.model = model or create_model(self.rag.settings, self.tools)

        graph = StateGraph(MiloState)
        graph.add_node("recuperar", self.retrieve)
        graph.add_node("milo", self.call_model)
        # Si una herramienta falla (p. ej. alimento desconocido), el error vuelve a Gemini para que lo corrija.
        graph.add_node("herramientas", ToolNode(self.tools, handle_tool_errors=True))
        graph.add_edge(START, "recuperar")
        graph.add_edge("recuperar", "milo")
        # tools_condition: si Gemini ha pedido una herramienta va a "herramientas"; si no, termina.
        graph.add_conditional_edges("milo", tools_condition, {"tools": "herramientas", END: END})
        graph.add_edge("herramientas", "milo")
        self.graph = graph.compile(checkpointer=self._memory(memory_path))

    def _memory(self, path):
        if path == ":memory:":
            from langgraph.checkpoint.memory import InMemorySaver

            return InMemorySaver()
        from langgraph.checkpoint.sqlite import SqliteSaver

        path = Path(path or Settings().storage_dir / "memoria.sqlite")
        path.parent.mkdir(parents=True, exist_ok=True)
        return SqliteSaver(sqlite3.connect(path, check_same_thread=False))

    # -- nodo 1
    def retrieve(self, state: MiloState) -> dict:
        questions = [m.content for m in state["messages"] if isinstance(m, HumanMessage)]
        query = questions[-1]
        if len(query.split()) < 6 and len(questions) > 1:
            # "¿Y cuántas calorías tiene?" no dice de qué habla: añado la pregunta anterior a la búsqueda.
            query = questions[-2] + " " + query
        return {"fragments": self.rag.retrieve(query, k=4)}

    # -- nodo 2
    def call_model(self, state: MiloState) -> dict:
        profile = UserProfile.model_validate(state.get("profile") or {})
        system = (
            self.rag.system_prompt
            + "\n\n# Perfil registrado del usuario\n"
            + describe_profile(profile, self.kitchen.catalog)
            + "\n\n<documentos>\n"
            + format_context(state.get("fragments") or [])
            + "\n</documentos>"
        )
        response = self.model.invoke([SystemMessage(content=system), *recent_history(state["messages"])])
        return {"messages": [response]}

    # -- uso desde el notebook, la terminal o Streamlit
    def ask(self, question: str, *, thread_id: str, profile: UserProfile | None = None) -> dict:
        if not question.strip() or not thread_id.strip():
            raise ValueError("La pregunta y el identificador de conversación son obligatorios")
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 16}
        previous = self.graph.get_state(config).values
        update: dict = {"messages": [HumanMessage(content=question)]}
        if profile is not None or not previous.get("profile"):
            update["profile"] = (profile or UserProfile()).model_dump(mode="json")
        before = len(previous.get("messages", []))
        state = self.graph.invoke(update, config=config)
        new = state["messages"][before:]
        return {
            "question": question,
            "answer": message_text(state["messages"][-1]),
            "fragments": state.get("fragments", []),
            "tools": [m.name for m in new if isinstance(m, ToolMessage)],
            "results": [
                {"tool": m.name, **m.artifact}
                for m in new
                if isinstance(m, ToolMessage) and isinstance(m.artifact, dict)
            ],
            "profile": state["profile"],
            "messages": state["messages"],
        }

    def history(self, thread_id: str) -> list:
        return self.graph.get_state({"configurable": {"thread_id": thread_id}}).values.get("messages", [])

    def get_profile(self, thread_id: str) -> UserProfile:
        values = self.graph.get_state({"configurable": {"thread_id": thread_id}}).values
        return UserProfile.model_validate(values.get("profile") or {})


def show_turn(turn: dict) -> None:
    """Imprime un turno en el notebook: herramientas usadas, fragmentos recuperados y respuesta."""
    print("Herramientas usadas:", ", ".join(turn["tools"]) or "ninguna (respuesta solo con RAG)")
    show_answer(
        RagAnswer(turn["question"], turn["fragments"], turn["answer"]), label="RESPUESTA DE MILO", width=160
    )


def is_ai_text(message) -> bool:
    return isinstance(message, AIMessage) and bool(message_text(message).strip()) and not message.tool_calls
