"""Grafo LangGraph con un Gemini simulado (sin API) y una prueba real marcada como --live."""

import pytest
from langchain_core.messages import AIMessage

from milo.agent import MiloAgent, recent_history
from milo.recipes import Kitchen


class ScriptedModel:
    """Doble de Gemini: devuelve respuestas preparadas y guarda lo que recibe."""

    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return next(self.replies)


class FakeRag:
    system_prompt = "Eres MILO (prueba)."

    def __init__(self):
        self.queries = []

    def retrieve(self, question, k=4):
        self.queries.append(question)
        return [
            {"citation": 1, "text": "Consume legumbres.", "metadata": {"source_id": "AESAN_2022", "page": 6}}
        ]


def tool_call(name, args, call_id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


@pytest.fixture(scope="module")
def kitchen():
    return Kitchen()


def make_agent(kitchen, replies):
    rag, model = FakeRag(), ScriptedModel(replies)
    return MiloAgent(rag=rag, kitchen=kitchen, memory_path=":memory:", model=model), rag, model


def test_graph_retrieves_then_calls_tool_then_answers(kitchen):
    agent, rag, model = make_agent(
        kitchen, [tool_call("ver_receta", {"recipe_id": "r001"}), AIMessage(content="Aquí la tienes.")]
    )
    turn = agent.ask("Quiero el bowl de pollo", thread_id="a")
    assert rag.queries == ["Quiero el bowl de pollo"]
    assert turn["tools"] == ["ver_receta"]
    assert turn["results"][0]["titulo"] == "Bowl de pollo y arroz"
    assert turn["answer"] == "Aquí la tienes."
    # Gemini recibió el system prompt con los fragmentos recuperados.
    assert "<documentos>" in model.calls[0][0].content and "legumbres" in model.calls[0][0].content


def test_memory_profile_and_thread_isolation(kitchen):
    agent, rag, model = make_agent(
        kitchen,
        [
            tool_call("guardar_perfil", {"dieta": "vegetariana", "no_me_gusta": ["tomate"]}),
            AIMessage(content="Guardado."),
            tool_call("buscar_recetas", {"comida": "cena"}, "c2"),
            AIMessage(content="Te propongo una cena."),
            AIMessage(content="Hola, soy MILO."),
        ],
    )
    agent.ask("Soy vegetariano y no me gusta el tomate", thread_id="uno")
    second = agent.ask("¿Qué ceno?", thread_id="uno")
    assert second["profile"]["restrictions"] == [{"kind": "diet", "value": "vegetarian"}]
    assert all(r["dieta"] in {"vegetariana", "vegana"} for r in second["results"][0]["recetas"])
    # La pregunta corta se completa con la anterior para buscar en Chroma.
    assert rag.queries[-1].startswith("Soy vegetariano")
    # El segundo turno envía a Gemini el historial del primero.
    assert any("Soy vegetariano" in str(m.content) for m in model.calls[2][1:])
    other = agent.ask("Hola", thread_id="dos")
    assert other["profile"]["restrictions"] == [] and len(other["messages"]) == 2


def test_shopping_list_uses_last_plan_from_memory(kitchen):
    agent, _, _ = make_agent(
        kitchen,
        [
            tool_call("plan_semanal", {"kcal_diarias": 2200, "dias": 2}),
            AIMessage(content="Menú listo."),
            tool_call("lista_compra", {}, "c2"),
            AIMessage(content="Lista lista."),
        ],
    )
    agent.ask("Menú de dos días", thread_id="p")
    turn = agent.ask("Ahora la lista de la compra", thread_id="p")
    assert turn["results"][0]["tipo"] == "lista_compra" and turn["results"][0]["total_productos"] > 5


def test_tool_error_goes_back_to_gemini(kitchen):
    agent, _, model = make_agent(
        kitchen, [tool_call("ver_receta", {"recipe_id": "r999"}), AIMessage(content="No tengo esa receta.")]
    )
    turn = agent.ask("Quiero la receta r999", thread_id="err")
    assert turn["answer"] == "No tengo esa receta."
    error = model.calls[1][-1]
    assert error.type == "tool" and "r999" in error.content


def test_recent_history_starts_on_user_message():
    from langchain_core.messages import HumanMessage

    messages = [HumanMessage(content=str(i)) if i % 2 == 0 else AIMessage(content=str(i)) for i in range(30)]
    history = recent_history(messages, turns=3)
    assert isinstance(history[0], HumanMessage) and len(history) == 6


@pytest.mark.live
def test_real_agent_memory_and_tools():
    agent = MiloAgent(memory_path=":memory:")
    first = agent.ask("Soy vegetariano. Recomiéndame una cena sencilla.", thread_id="live")
    second = agent.ask("¿Cuántas proteínas tiene esa receta?", thread_id="live")
    assert first["profile"]["restrictions"] == [{"kind": "diet", "value": "vegetarian"}]
    assert {"buscar_recetas", "ver_receta"} & set(first["tools"] + second["tools"])
    assert len(second["messages"]) > len(first["messages"])
