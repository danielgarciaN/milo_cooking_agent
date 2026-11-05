"""MILO — AI Nutrition Chef. Interfaz web con Streamlit.

    streamlit run app.py

La app no contiene lógica propia del agente: importa el mismo MiloAgent (LangGraph + RAG + Gemini)
y la misma cocina (Kitchen) que uso en el notebook. Aquí solo hay pantallas y estilos.
"""

from __future__ import annotations

import contextlib
import html
import os
import sys
import uuid
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))  # Así Python encuentra el paquete milo aunque no esté instalado.
MASCOT = ROOT / "assets" / "milo_small.png"
ORANGE, CREAM, GREEN, CHARCOAL = "#F49B43", "#FFF6E9", "#86AD8F", "#292D32"

st.set_page_config(page_title="MILO — AI Nutrition Chef", page_icon=str(MASCOT), layout="wide")

# En Streamlit Cloud la clave se guarda en "Secrets"; en local se lee del archivo .env.
with contextlib.suppress(Exception):  # En local no hay secrets.toml y st.secrets lanza un error.
    if "GOOGLE_API_KEY" in st.secrets:
        os.environ.setdefault("GOOGLE_API_KEY", st.secrets["GOOGLE_API_KEY"])

from milo.agent import MiloAgent
from milo.models import DietaryRestriction, UserProfile
from milo.rag import location
from milo.recipes import ALLERGENS_ES, MEAL_NAMES, Kitchen, describe_profile

# ---------------------------------------------------------------- estilos

st.markdown(
    f"""
<style>
.block-container {{ padding-top: 2rem; max-width: 1100px; }}
[data-testid="stSidebar"] {{ border-right: 1px solid #F6D7B0; }}
[data-testid="stSidebar"] img, .st-key-mascot img {{ border-radius: 28px; box-shadow: 0 6px 24px rgba(244,155,67,.18); }}
h1, h2, h3 {{ color: {CHARCOAL}; font-weight: 800; letter-spacing: -0.5px; }}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius: 999px; border: 1.5px solid {ORANGE}; font-weight: 700; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button {{ background: {ORANGE} !important; color: white !important; }}
.stFormSubmitButton > button p, .stButton > button[kind="primary"] p {{ color: white !important; font-weight: 800; }}
.brand {{ margin: .4rem 0 .9rem; }}
.brand .wordmark {{ font-size: 2.7rem; font-weight: 900; color: {CHARCOAL}; line-height: 1; letter-spacing: -1.5px; }}
.brand .wordmark span {{ color: {ORANGE}; }}
.brand .slogan {{ color: {GREEN}; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; font-size: .78rem; }}
.hero {{ background: white; border-radius: 28px; padding: 1.6rem 2rem; box-shadow: 0 8px 30px rgba(244,155,67,.15); }}
.hero h1 {{ font-size: 2.3rem; margin-bottom: .3rem; }}
.card {{ background: white; border-radius: 22px; padding: 1.1rem 1.3rem; margin: .4rem 0 .6rem;
  box-shadow: 0 4px 18px rgba(41,45,50,.07); border: 1px solid #F6E3CB; }}
.card h4 {{ margin: 0 0 .35rem; font-weight: 800; color: {CHARCOAL}; }}
.chip {{ display: inline-block; padding: .12rem .65rem; border-radius: 999px; font-size: .78rem; font-weight: 700;
  margin: 0 .3rem .3rem 0; background: {CREAM}; color: {CHARCOAL}; border: 1px solid #F6D7B0; }}
.chip.green {{ background: #E6F0E8; border-color: #C9DECE; color: #3F6B4A; }}
.chip.orange {{ background: {ORANGE}; border-color: {ORANGE}; color: white; }}
.chip.warn {{ background: #FFF1F0; border-color: #F5C2BE; color: #9B3A33; }}
.macros {{ display: flex; gap: .5rem; flex-wrap: wrap; margin: .5rem 0; }}
.macro {{ flex: 1 1 90px; background: {CREAM}; border-radius: 16px; padding: .5rem .7rem; text-align: center; }}
.macro b {{ display: block; font-size: 1.35rem; font-weight: 900; color: {CHARCOAL}; }}
.macro small {{ color: #6B6F75; font-weight: 700; text-transform: uppercase; font-size: .68rem; letter-spacing: .5px; }}
.macro.kcal {{ background: {ORANGE}; }} .macro.kcal b, .macro.kcal small {{ color: white; }}
.bar {{ display: flex; height: 10px; border-radius: 999px; overflow: hidden; margin: .35rem 0 .2rem; }}
.legend {{ font-size: .75rem; color: #6B6F75; font-weight: 600; }}
.source {{ font-size: .85rem; border-left: 4px solid #F6D7B0; padding: .2rem .7rem; margin: .4rem 0; }}
.source.cited {{ border-left-color: {ORANGE}; }}
.muted {{ color: #7A7E84; font-size: .85rem; }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- recursos compartidos


@st.cache_resource(show_spinner="Encendiendo los fogones de MILO…")
def load_agent() -> MiloAgent:
    return MiloAgent()


@st.cache_resource
def load_kitchen() -> Kitchen:
    return Kitchen()


kitchen = load_kitchen()
state = st.session_state
if "thread_id" not in state:
    # El identificador de conversación va en la URL: al recargar la página, MILO recuerda la charla.
    state.thread_id = st.query_params.get("c") or uuid.uuid4().hex[:12]
    st.query_params["c"] = state.thread_id
    state.turns = None
    state.profile = UserProfile()
    state.plan = None
    state.pending = None
    state.page = "Chat"


def esc(value) -> str:
    return html.escape(str(value))


def fmt(value, unit: str = "", digits: int = 0) -> str:
    return "sin dato" if value is None else f"{value:.{digits}f}{unit}"


# ---------------------------------------------------------------- componentes visuales


def macro_tiles(values: dict, label: str = "por ración") -> str:
    kcal_from = {
        "Proteína": (values.get("protein_g") or 0) * 4,
        "Hidratos": (values.get("carbs_g") or 0) * 4,
        "Grasa": (values.get("fat_g") or 0) * 9,
    }
    total = sum(kcal_from.values()) or 1
    colors = {"Proteína": GREEN, "Hidratos": ORANGE, "Grasa": "#F6C58F"}
    bar = "".join(
        f'<div style="width:{v / total * 100:.1f}%;background:{colors[k]}"></div>'
        for k, v in kcal_from.items()
    )
    legend = " · ".join(f"{k} {v / total * 100:.0f}%" for k, v in kcal_from.items())
    return f"""
<div class="macros">
  <div class="macro kcal"><b>{fmt(values.get("kcal"))}</b><small>kcal {label}</small></div>
  <div class="macro"><b>{fmt(values.get("protein_g"), " g", 1)}</b><small>Proteína</small></div>
  <div class="macro"><b>{fmt(values.get("carbs_g"), " g", 1)}</b><small>Hidratos</small></div>
  <div class="macro"><b>{fmt(values.get("fat_g"), " g", 1)}</b><small>Grasa</small></div>
  <div class="macro"><b>{fmt(values.get("fiber_g"), " g", 1)}</b><small>Fibra</small></div>
</div>
<div class="bar">{bar}</div><div class="legend">Energía según macro: {legend}</div>"""


def recipe_card(card: dict, *, key: str, expanded: bool = False) -> None:
    chips = [f'<span class="chip orange">{esc(card["dieta"])}</span>']
    if card.get("tiempo_min"):
        chips.append(f'<span class="chip">⏱ {card["tiempo_min"]} min</span>')
    chips.append(f'<span class="chip">{esc(card.get("dificultad", "fácil"))}</span>')
    chips += [f'<span class="chip green">{esc(MEAL_NAMES.get(m, m))}</span>' for m in card.get("comidas", [])]
    chips += [f'<span class="chip warn">⚠ {esc(a)}</span>' for a in card.get("alergenos", [])]
    servings = f" · {card['raciones']} raciones" if card.get("raciones", 1) > 1 else ""
    st.markdown(
        f"""<div class="card"><h4>{esc(card["titulo"])}{servings}</h4>{"".join(chips)}
        {macro_tiles(card["por_racion"])}</div>""",
        unsafe_allow_html=True,
    )
    with st.expander("Ingredientes y preparación", expanded=expanded):
        left, right = st.columns([1, 1.3])
        with left:
            st.markdown("**Ingredientes**")
            for item in card["ingredientes"]:
                st.markdown(f"- {item['nombre']}: **{item['gramos']:.0f} g**")
        with right:
            st.markdown("**Preparación**")
            for n, step in enumerate(card["pasos"], 1):
                st.markdown(f"{n}. {step}")
        notes = [card.get("nota")] + card.get("avisos", [])
        st.caption(" ".join(n for n in notes if n) + " " + card.get("base_del_calculo", ""))


def plan_chart(plan: dict) -> None:
    data = pd.DataFrame([{"Día": d["dia"], "kcal": d["total"]["kcal"]} for d in plan["dias"]])
    bars = (
        alt.Chart(data)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, color=ORANGE)
        .encode(
            x=alt.X("Día:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("kcal:Q", title="kcal"),
            tooltip=["Día", "kcal"],
        )
    )
    target = (
        alt.Chart(pd.DataFrame({"kcal": [plan["kcal_objetivo"]]}))
        .mark_rule(color=GREEN, strokeDash=[6, 4], size=3)
        .encode(y="kcal:Q")
    )
    st.altair_chart((bars + target).properties(height=240), width="stretch")
    st.caption("Barras: kcal de cada día · Línea verde: tu objetivo.")


def plan_view(plan: dict, *, key: str) -> None:
    avg = plan["media_diaria"]
    cols = st.columns(4)
    cols[0].metric("Objetivo", f"{plan['kcal_objetivo']:.0f} kcal")
    gap = avg["kcal"] - plan["kcal_objetivo"]
    delta = f"{gap:+.0f} kcal" if abs(gap) >= 1 else None
    cols[1].metric("Media diaria", f"{avg['kcal']:.0f} kcal", delta, delta_color="off")
    cols[2].metric("Proteína media", f"{avg['protein_g']:.0f} g")
    cols[3].metric("Días", len(plan["dias"]))
    plan_chart(plan)
    for tab, day in zip(st.tabs([d["dia"] for d in plan["dias"]]), plan["dias"], strict=True):
        with tab:
            for meal in day["comidas"]:
                ingredients = ", ".join(
                    f"{i['nombre'].split(',')[0]} {i['gramos']:.0f} g" for i in meal["ingredientes"]
                )
                st.markdown(
                    f"""<div class="card"><span class="chip green">{esc(meal["comida"])}</span>
                    <span class="chip orange">{meal["kcal"]:.0f} kcal</span>
                    <span class="chip">P {meal["protein_g"]:.0f} g · H {meal["carbs_g"]:.0f} g · G {meal["fat_g"]:.0f} g</span>
                    <h4>{esc(meal["titulo"])}</h4><div class="muted">{esc(ingredients)}</div></div>""",
                    unsafe_allow_html=True,
                )
            t = day["total"]
            st.markdown(
                f"**Total del día:** {t['kcal']:.0f} kcal · {t['protein_g']:.0f} g proteína · "
                f"{t['carbs_g']:.0f} g hidratos · {t['fat_g']:.0f} g grasa"
            )
    for note in plan.get("avisos", []):
        st.caption(note)


def shopping_view(shopping: dict, *, key: str) -> None:
    columns = st.columns(2)
    lines = ["Lista de la compra de MILO", ""]
    for n, category in enumerate(shopping["categorias"]):
        with columns[n % 2]:
            st.markdown(f"**{category['categoria']}**")
            for item in category["items"]:
                label = f"{item['nombre']} — {item['gramos']:.0f} g"
                st.checkbox(label, key=f"{key}-{item['food_id']}")
                lines.append(f"[ ] {label}")
        lines.append("")
    st.caption(shopping["nota"])
    st.download_button("Descargar lista (.txt)", "\n".join(lines), "lista_compra_milo.txt", key=f"dl-{key}")


def search_view(result: dict, *, key: str) -> None:
    for recipe in result["recetas"]:
        extra = ""
        if recipe.get("te_falta") is not None:
            extra = f" · te falta: {', '.join(i.split(',')[0] for i in recipe['te_falta']) or 'nada 🎉'}"
        st.markdown(
            f"""<div class="card"><h4>{esc(recipe["titulo"])}</h4>
            <span class="chip orange">{recipe["kcal"]:.0f} kcal</span><span class="chip">P {recipe["protein_g"]:.0f} g</span>
            <span class="chip">⏱ {recipe["tiempo_min"]} min</span><span class="chip green">{esc(recipe["dieta"])}</span>
            <div class="muted">{esc(extra)}</div></div>""",
            unsafe_allow_html=True,
        )


def render_result(result: dict, key: str) -> None:
    kind = result.get("tipo")
    if "error" in result:
        return
    if kind in {"receta", "plato"}:
        recipe_card(result, key=key)
    elif kind == "opciones_sustitucion":
        with st.expander(
            f"🔁 Alternativas para {result['ingrediente'].split(',')[0].lower()}", expanded=True
        ):
            for option in result["opciones"]:
                m = option["receta_por_racion"]
                st.markdown(
                    f"- **{option['alimento']}** ({option['gramos']:.0f} g) → receta: {m['kcal']:.0f} kcal · "
                    f"{m['protein_g']:.0f} g proteína · {m['fat_g']:.0f} g grasa"
                )
    elif kind == "sustitucion":
        st.markdown(
            f"🔁 **{esc(result['cambio']['quitar'])}** → **{esc(result['cambio']['poner'])}** "
            f"({result['antes_por_racion']['kcal']:.0f} → {result['despues_por_racion']['kcal']:.0f} kcal)"
        )
        recipe_card(result["receta"], key=key)
    elif kind == "plan":
        with st.expander("📅 Ver el menú completo", expanded=True):
            plan_view(result, key=key)
        state.plan = result
    elif kind == "lista_compra":
        with st.expander("🛒 Lista de la compra", expanded=True):
            shopping_view(result, key=key)
    elif kind == "busqueda" and result["recetas"]:
        with st.expander(f"🍳 {len(result['recetas'])} recetas encontradas"):
            search_view(result, key=key)


def sources_view(fragments: list[dict], answer: str) -> None:
    from milo.rag import cited_numbers

    cited = cited_numbers(answer)
    with st.expander(f"📚 Fragmentos recuperados de ChromaDB ({len(fragments)})"):
        st.caption(
            "Así funciona el RAG: busco tu pregunta en mis documentos y Gemini responde con estos fragmentos."
        )
        for f in fragments:
            meta = f["metadata"]
            mark = "cited" if f["citation"] in cited else ""
            distance = f" · distancia {f['distance']:.3f}" if "distance" in f else ""
            text = esc(f["text"][:320]) + ("…" if len(f["text"]) > 320 else "")
            st.markdown(
                f"""<div class="source {mark}"><b>[{f["citation"]}] {esc(meta["source_id"])}</b> —
                {esc(location(meta))}<span class="muted">{distance}</span><br>{text}</div>""",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------- conversación


def restore_turns(agent: MiloAgent) -> list[dict]:
    """Reconstruye la conversación guardada en la memoria de LangGraph (SQLite) al recargar la página."""
    from langchain_core.messages import HumanMessage, ToolMessage

    from milo.agent import is_ai_text
    from milo.rag import message_text

    turns, results = [], []
    for message in agent.history(state.thread_id):
        if isinstance(message, HumanMessage):
            turns.append({"role": "user", "content": message.content})
            results = []
        elif isinstance(message, ToolMessage) and isinstance(message.artifact, dict):
            results.append(message.artifact)
        elif is_ai_text(message):
            turns.append(
                {"role": "assistant", "content": message_text(message), "results": results, "fragments": []}
            )
    return turns


def ask_milo(question: str) -> None:
    state.turns.append({"role": "user", "content": question})
    try:
        agent = load_agent()
        with st.spinner("MILO está cocinando la respuesta…"):
            turn = agent.ask(question, thread_id=state.thread_id, profile=state.profile)
        state.profile = UserProfile.model_validate(turn["profile"])
        state.turns.append(
            {
                "role": "assistant",
                "content": turn["answer"],
                "results": turn["results"],
                "fragments": turn["fragments"],
            }
        )
    except RuntimeError as exc:
        state.turns.append({"role": "assistant", "content": f"⚠️ {exc}", "results": [], "fragments": []})
    except Exception as exc:  # noqa: BLE001 - muestro el problema de forma comprensible
        message = str(exc)
        if "503" in message or "UNAVAILABLE" in message or "429" in message:
            message = "Gemini está saturado en este momento. Espera unos segundos y vuelve a preguntar."
        state.turns.append(
            {
                "role": "assistant",
                "content": f"⚠️ No he podido responder: {message[:300]}",
                "results": [],
                "fragments": [],
            }
        )


SUGGESTIONS = [
    "Tengo pollo, arroz, aguacate y huevos. Quiero una cena de unas 800 kcal con bastante proteína.",
    "¿Qué recomienda la documentación sobre una alimentación equilibrada?",
    "Soy vegetariano y no me gusta el tomate. ¿Qué ceno hoy?",
    "Hazme un menú de 3 días de unas 2.500 kcal al día.",
    "No tengo aguacate, ¿por qué lo puedo sustituir en las tostadas?",
    "¿Cuántos huevos puedo comer a la semana?",
]


def page_chat() -> None:
    if state.turns is None:
        try:
            state.turns = restore_turns(load_agent())
        except Exception:  # noqa: BLE001 - sin clave todavía: la conversación empieza vacía
            state.turns = []
    if state.pending:
        question, state.pending = state.pending, None
        ask_milo(question)
    if not state.turns:
        left, right = st.columns([1, 2.2], vertical_alignment="center")
        with left.container(key="mascot"):
            st.image(str(MASCOT), width="stretch")
        right.markdown(
            """<div class="hero"><h1>¡Hola! Soy MILO. ¿Qué cocinamos hoy?</h1>
            <p>Dime qué tienes en la nevera, tu objetivo o tus manías con la comida. Busco en mis documentos,
            calculo los macros con datos reales de USDA y recuerdo lo que me cuentas.</p></div>""",
            unsafe_allow_html=True,
        )
        st.markdown("#### Prueba a preguntarme")
        cols = st.columns(2)
        for n, suggestion in enumerate(SUGGESTIONS):
            if cols[n % 2].button(suggestion, key=f"sug{n}", width="stretch"):
                state.pending = suggestion
                st.rerun()
    for n, turn in enumerate(state.turns):
        avatar = str(MASCOT) if turn["role"] == "assistant" else "🧑‍🍳"
        with st.chat_message(turn["role"], avatar=avatar):
            st.markdown(turn["content"])
            for m, result in enumerate(turn.get("results", [])):
                render_result(result, key=f"t{n}r{m}")
            if turn.get("fragments"):
                sources_view(turn["fragments"], turn["content"])
    if question := st.chat_input("Escribe a MILO… (p. ej. «¿qué hago con garbanzos y espinacas?»)"):
        ask_milo(question)
        st.rerun()


# ---------------------------------------------------------------- mi nevera

FOOD_OPTIONS = sorted(
    {f.name_es for f in kitchen.catalog.foods.values() if f.nutrients_per_100g.kcal is not None}
)


def page_fridge() -> None:
    st.markdown("## 🧊 Mi nevera")
    st.markdown(
        "Marca lo que tienes y te digo qué recetas puedes preparar y qué te falta. *(Sin IA: búsqueda directa en mi recetario.)*"
    )
    chosen = st.multiselect("¿Qué tienes en casa?", FOOD_OPTIONS, placeholder="Busca: pollo, arroz, huevo…")
    c1, c2, c3 = st.columns(3)
    meal = c1.selectbox("Para", ["Cualquier comida", "desayuno", "comida", "cena", "snack"])
    max_kcal = c2.slider("Máximo de kcal por ración", 150, 1200, 1200, 50)
    max_time = c3.slider("Tiempo máximo (min)", 5, 60, 60, 5)
    if not chosen:
        st.info("Añade al menos un ingrediente para empezar.")
        return
    result = kitchen.search(
        state.profile,
        ingredientes=chosen,
        comida=None if meal == "Cualquier comida" else meal,
        max_kcal=max_kcal,
        tiempo_max=max_time,
        limite=9,
    )
    if result["descartadas_por_perfil"]:
        st.caption(
            f"He descartado {result['descartadas_por_perfil']} recetas por tu perfil ({describe_profile(state.profile, kitchen.catalog)})."
        )
    if not result["recetas"]:
        st.warning("No encuentro recetas con esos ingredientes y filtros. Prueba a quitar algún filtro.")
    cols = st.columns(3)
    for n, recipe in enumerate(result["recetas"]):
        with cols[n % 3]:
            missing = recipe["te_falta"]
            st.markdown(
                f"""<div class="card"><h4>{esc(recipe["titulo"])}</h4>
                <span class="chip orange">{recipe["kcal"]:.0f} kcal</span><span class="chip">P {recipe["protein_g"]:.0f} g</span>
                <span class="chip">⏱ {recipe["tiempo_min"]} min</span>
                <div class="muted">✅ Tienes {len(recipe["tienes"])} · 🛒 Te falta: {esc(", ".join(i.split(",")[0] for i in missing) or "nada")}</div></div>""",
                unsafe_allow_html=True,
            )
            with st.popover("Ver receta", width="stretch"):
                recipe_card(kitchen.view(state.profile, recipe["recipe_id"]), key=f"fr{n}", expanded=True)
    names = ", ".join(c.split(",")[0].lower() for c in chosen)
    if st.button(f"💬 Pedir a MILO una idea con {names}", type="primary"):
        state.pending = f"Tengo {names}. ¿Qué me recomiendas cocinar?"
        state.goto = "Chat"
        st.rerun()


# ---------------------------------------------------------------- plan semanal


def page_plan() -> None:
    st.markdown("## 📅 Plan semanal")
    st.markdown(
        "Genero un menú con recetas compatibles con tu perfil y ajusto las cantidades a tu objetivo de kcal."
    )
    with st.form("form_plan"):
        c1, c2, c3 = st.columns(3)
        kcal = c1.slider("kcal al día", 1200, 4500, state.profile.daily_kcal or 2000, 50)
        days = c2.slider("Días", 1, 7, 7)
        meals = c3.radio(
            "Comidas al día",
            [4, 3],
            format_func=lambda n: f"{n} ({'con snack' if n == 4 else 'sin snack'})",
            horizontal=True,
        )
        if st.form_submit_button("Generar menú", type="primary", width="stretch"):
            result = kitchen.weekly_plan(state.profile, kcal_diarias=kcal, dias=days, comidas=meals)
            if "error" in result:
                st.error(result["error"])
            else:
                state.plan = result
    if state.plan:
        plan_view(state.plan, key="plan")
        st.markdown("### 🛒 Lista de la compra")
        shopping_view(kitchen.shopping_list(state.plan), key="plan-list")


# ---------------------------------------------------------------- perfil

ALLERGEN_OPTIONS = {v: k for k, v in ALLERGENS_ES.items()}
GOALS = ["Comer más sano", "Mantener peso", "Perder peso", "Ganar masa muscular"]


def page_profile() -> None:
    st.markdown("## 👤 Mi perfil")
    st.markdown("MILO usa estos datos para filtrar recetas con Python antes de recomendar nada.")
    profile = state.profile
    diets = {"Sin restricciones": None, "Vegetariana": "vegetarian", "Vegana": "vegan"}
    current_diet = next((r.value for r in profile.restrictions if r.kind == "diet"), None)
    by_kind = lambda kind: [ALLERGENS_ES[r.value] for r in profile.restrictions if r.kind == kind]
    names = {f.food_id: f.name_es for f in kitchen.catalog.foods.values()}
    with st.form("form_perfil"):
        c1, c2 = st.columns(2)
        diet = c1.selectbox("Dieta", list(diets), index=list(diets.values()).index(current_diet))
        goal = c2.selectbox(
            "Objetivo", GOALS, index=GOALS.index(profile.goal) if profile.goal in GOALS else 0
        )
        allergies = c1.multiselect(
            "Alergias", list(ALLERGEN_OPTIONS), default=by_kind("allergy"), placeholder="Ninguna"
        )
        intolerances = c2.multiselect(
            "Intolerancias", list(ALLERGEN_OPTIONS), default=by_kind("intolerance"), placeholder="Ninguna"
        )
        disliked = st.multiselect(
            "Alimentos que no me gustan", list(names), default=sorted(profile.disliked_food_ids & names.keys()),
            format_func=names.get, placeholder="Ninguno",
        )  # fmt: skip
        kcal = c1.number_input("kcal diarias aproximadas (opcional)", 0, 6000, profile.daily_kcal or 0, 50)
        preferences = c2.text_input("Preferencias (separadas por comas)", ", ".join(profile.preferences))
        if st.form_submit_button("Guardar perfil", type="primary", width="stretch"):
            restrictions = [DietaryRestriction(kind="diet", value=diets[diet])] if diets[diet] else []
            restrictions += [DietaryRestriction(kind="allergy", value=ALLERGEN_OPTIONS[a]) for a in allergies]
            restrictions += [
                DietaryRestriction(kind="intolerance", value=ALLERGEN_OPTIONS[a]) for a in intolerances
            ]
            state.profile = UserProfile(
                goal=goal,
                daily_kcal=kcal or None,
                restrictions=restrictions,
                disliked_food_ids=set(disliked),
                preferences=[p.strip() for p in preferences.split(",") if p.strip()],
            )
            st.success("¡Perfil guardado! MILO lo tendrá en cuenta en el chat, la nevera y el menú.")
    st.markdown(
        f'<div class="card"><b>Resumen:</b> {esc(describe_profile(state.profile, kitchen.catalog))}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "El perfil se guarda en la memoria de esta conversación (archivo local storage/memoria.sqlite). "
        "MILO da educación nutricional general: no sustituye a un profesional sanitario."
    )


# ---------------------------------------------------------------- barra lateral y navegación

PAGES = {
    "Chat": ("💬", page_chat),
    "Mi nevera": ("🧊", page_fridge),
    "Plan semanal": ("📅", page_plan),
    "Mi perfil": ("👤", page_profile),
}

with st.sidebar:
    st.image(str(MASCOT), width="stretch")
    st.markdown(
        '<div class="brand"><div class="wordmark">milo<span>.</span></div>'
        '<div class="slogan">Eat smart. Cook happy.</div></div>',
        unsafe_allow_html=True,
    )
    if state.get("goto"):  # Salto desde un botón (p. ej. "Pedir a MILO"): se aplica antes de dibujar el menú.
        state.page = state.pop("goto")
    st.radio(
        "Secciones",
        list(PAGES),
        key="page",
        format_func=lambda p: f"{PAGES[p][0]}  {p}",
        label_visibility="collapsed",
    )
    st.markdown(
        f'<div class="muted"><b>Tu perfil:</b> {esc(describe_profile(state.profile, kitchen.catalog))}</div>',
        unsafe_allow_html=True,
    )
    st.write("")
    if st.button("🧹 Nueva conversación", width="stretch"):
        state.thread_id = uuid.uuid4().hex[:12]
        st.query_params["c"] = state.thread_id
        state.turns, state.plan, state.profile = [], None, UserProfile()
        st.rerun()
    st.caption("Gemini · RAG con ChromaDB · LangGraph\n\nDatos: USDA FoodData Central y AESAN (2022).")

PAGES[state.page][1]()
