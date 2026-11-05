"""MILO — AI Nutrition Chef. Interfaz web con Streamlit.

    streamlit run app.py

La app no contiene lógica propia del agente: importa el mismo MiloAgent (LangGraph + RAG + Gemini)
y la misma cocina (Kitchen) que uso en el notebook. Aquí solo hay pantallas y estilos.

- Colores y tipografías del tema: .streamlit/config.toml
- Estilos adicionales (tarjetas, chat centrado): constante CSS de este archivo
- Iconos: Material Symbols (incluidos en Streamlit) e iconos SVG de Lucide en la constante ICONS
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
MASCOT = ROOT / "assets" / "milo_small.png"  # Mascota oficial con fondo transparente.
ORANGE, CREAM, GREEN, CHARCOAL = "#F49B43", "#FFF6E9", "#86AD8F", "#292D32"

st.set_page_config(page_title="MILO — AI Nutrition Chef", page_icon=str(MASCOT), layout="wide")

# En Streamlit Cloud la clave se guarda en "Secrets"; en local se lee del archivo .env.
with contextlib.suppress(Exception):  # En local no hay secrets.toml y st.secrets lanza un error.
    if "GOOGLE_API_KEY" in st.secrets:
        os.environ.setdefault("GOOGLE_API_KEY", st.secrets["GOOGLE_API_KEY"])

from milo.agent import MiloAgent
from milo.models import DietaryRestriction, UserProfile
from milo.rag import cited_numbers, location
from milo.recipes import ALLERGENS_ES, MEAL_NAMES, Kitchen, describe_profile

# ---------------------------------------------------------------- iconos (Lucide, licencia ISC)

ICONS = {
    "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "egg": '<path d="M12 22c6.23-.05 7.87-5.57 7.5-10-.36-4.34-3.95-9.96-7.5-10-3.55.04-7.14 5.66-7.5 10-.37 4.43 1.27 9.95 7.5 10z"/>',
    "wheat": '<path d="M2 22 16 8"/><path d="M3.47 12.53 5 11l1.53 1.53a3.5 3.5 0 0 1 0 4.94L5 19l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z"/><path d="M7.47 8.53 9 7l1.53 1.53a3.5 3.5 0 0 1 0 4.94L9 15l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z"/><path d="M11.47 4.53 13 3l1.53 1.53a3.5 3.5 0 0 1 0 4.94L13 11l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z"/><path d="M20 2h2v2a4 4 0 0 1-4 4h-2V6a4 4 0 0 1 4-4Z"/>',
    "droplet": '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>',
    "leaf": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "chef": '<path d="M17 21a1 1 0 0 0 1-1v-5.35c0-.457.316-.844.727-1.041a4 4 0 0 0-2.134-7.589 5 5 0 0 0-9.186 0 4 4 0 0 0-2.134 7.588c.411.198.727.585.727 1.041V20a1 1 0 0 0 1 1Z"/><path d="M6 17h12"/>',
    "utensils": '<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "cart": '<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>',
    "fridge": '<path d="M5 6a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6Z"/><path d="M5 10h14"/><path d="M15 7v6"/>',
    "calendar": '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "repeat": '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
}  # fmt: skip


def icon(name: str, size: int = 16) -> str:
    return (
        f'<svg class="ico" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'
    )


# ---------------------------------------------------------------- estilos

CSS = f"""
<style>
.block-container {{ padding-top: 2.2rem; max-width: 1100px; }}
[data-testid="stSidebar"] {{ border-right: 1px solid #F6D7B0; }}
.stMarkdown p, .stMarkdown li {{ line-height: 1.6; }}
h1, h2, h3, h4 {{ color: {CHARCOAL}; letter-spacing: -0.3px; }}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, [data-testid="stPopover"] button {{
  border-radius: 999px; border: 1.5px solid {ORANGE}; font-weight: 600; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button {{ background: {ORANGE}; color: white; }}
.stButton > button[kind="primary"] p, .stFormSubmitButton > button p {{ color: white; font-weight: 700; }}
.ico {{ display: inline-block; vertical-align: -0.15em; flex-shrink: 0; }}

/* Marca y mascota: imagen transparente, sin recuadros ni sombras. */
.st-key-side-mascot, .st-key-hero-mascot {{ align-items: center; }}
.brand {{ text-align: center; margin: -.4rem 0 1rem; }}
.brand .wordmark {{ font-family: 'Nunito', sans-serif; font-size: 2.6rem; font-weight: 900; color: {CHARCOAL};
  line-height: 1; letter-spacing: -1.5px; }}
.brand .wordmark span {{ color: {ORANGE}; }}
.brand .slogan {{ color: {GREEN}; font-weight: 700; letter-spacing: 1.6px; text-transform: uppercase; font-size: .72rem; }}
.profile-box {{ font-size: .88rem; color: #5F6369; background: white; border-radius: 16px; padding: .7rem .9rem;
  border: 1px solid #F6E3CB; margin: .6rem 0; line-height: 1.45; }}

/* Cabecera de cada sección */
.page-title {{ display: flex; align-items: center; gap: .8rem; margin-bottom: .2rem; }}
.page-title .badge {{ width: 46px; height: 46px; border-radius: 14px; background: {ORANGE}; color: white;
  display: flex; align-items: center; justify-content: center; }}
.page-title h2 {{ margin: 0; padding: 0; font-size: 2rem; }}
.page-sub {{ color: #5F6369; margin: .3rem 0 1.2rem; }}

/* Bienvenida del chat */
.hero {{ text-align: center; margin: 0 auto 1.4rem; max-width: 640px; }}
.hero h1 {{ font-size: 2.3rem; line-height: 1.15; margin: .2rem 0 .6rem; padding: 0; }}
.hero p {{ color: #4F535A; font-size: 1.05rem; }}
.st-key-suggestions button {{ min-height: 3.6rem; text-align: left; background: white; border: 1px solid #F3D9B8;
  border-radius: 18px; font-weight: 500; }}
.st-key-suggestions button * {{ white-space: normal; overflow: visible; text-overflow: clip; }}
.st-key-suggestions button:hover {{ border-color: {ORANGE}; color: {CHARCOAL}; }}

/* Tarjetas */
.card {{ background: white; border-radius: 22px; padding: 1.1rem 1.3rem; margin: .4rem 0 .7rem;
  box-shadow: 0 4px 18px rgba(41,45,50,.06); border: 1px solid #F6E3CB; }}
.card h4 {{ margin: 0 0 .5rem; padding: 0; font-size: 1.2rem; color: {CHARCOAL}; }}
.chips {{ display: flex; flex-wrap: wrap; gap: .35rem; margin-bottom: .2rem; }}
.chip {{ display: inline-flex; align-items: center; gap: .3rem; padding: .18rem .7rem; border-radius: 999px;
  font-size: .82rem; font-weight: 600; background: {CREAM}; color: {CHARCOAL}; border: 1px solid #F6D7B0; }}
.chip.green {{ background: #E9F2EB; border-color: #C9DECE; color: #3F6B4A; }}
.chip.orange {{ background: {ORANGE}; border-color: {ORANGE}; color: white; }}
.chip.warn {{ background: #FFF1EF; border-color: #F5C2BE; color: #9B3A33; }}
.macros {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .5rem; margin: .7rem 0 .4rem; }}
.macro {{ background: {CREAM}; border-radius: 16px; padding: .55rem .4rem; text-align: center; }}
.macro b {{ display: block; font-family: 'Nunito', sans-serif; font-size: 1.35rem; font-weight: 900; color: {CHARCOAL}; }}
.macro small {{ display: inline-flex; align-items: center; gap: .25rem; color: #6B6F75; font-weight: 600; font-size: .78rem; }}
.macro.kcal {{ background: {ORANGE}; }} .macro.kcal b, .macro.kcal small {{ color: white; }}
.bar {{ display: flex; height: 9px; border-radius: 999px; overflow: hidden; margin: .4rem 0 .25rem; }}
.legend, .muted {{ color: #6B6F75; font-size: .88rem; }}
.status {{ display: flex; flex-wrap: wrap; gap: .4rem 1rem; margin-top: .6rem; color: #5F6369; font-size: .9rem; }}
.status span {{ display: inline-flex; align-items: flex-start; gap: .35rem; }}
.status .ico {{ margin-top: .2em; }}
.source {{ font-size: .9rem; border-left: 4px solid #F6D7B0; padding: .25rem .8rem; margin: .5rem 0; line-height: 1.5; }}
.source.cited {{ border-left-color: {ORANGE}; }}

@media (max-width: 640px) {{
  .block-container {{ padding-top: 1rem; }}
  .hero h1 {{ font-size: 1.7rem; }}
  .page-title h2 {{ font-size: 1.6rem; }}
  .macros {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
  .macro b {{ font-size: 1.1rem; }}
}}
</style>
"""

# Solo en el chat: columna centrada de ~820 px, también para la caja de escritura (estilo ChatGPT).
CHAT_CSS = """
<style>
[data-testid="stMainBlockContainer"], [data-testid="stBottomBlockContainer"] { max-width: 820px; }
[data-testid="stChatMessage"] .stMarkdown p, [data-testid="stChatMessage"] .stMarkdown li { font-size: 17px; line-height: 1.6; }
[data-testid="stChatMessage"] { padding: .6rem 0; margin-bottom: .4rem; background: transparent; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


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
    return "—" if value is None else f"{value:.{digits}f}{unit}"


def short(name: str) -> str:
    return name.split(",")[0]


def page_header(icon_name: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="page-title"><div class="badge">{icon(icon_name, 24)}</div><h2>{esc(title)}</h2></div>'
        f'<p class="page-sub">{subtitle}</p>',
        unsafe_allow_html=True,
    )


def chips(*items: tuple[str, str | None, str]) -> str:
    """Cada chip es (texto, icono o None, estilo)."""
    return (
        '<div class="chips">'
        + "".join(
            f'<span class="chip {style}">{icon(name, 14) if name else ""}{esc(text)}</span>'
            for text, name, style in items
        )
        + "</div>"
    )


# ---------------------------------------------------------------- componentes visuales


def summary_chips(recipe: dict, *, diet: bool = True) -> str:
    """Chips de una receta en una lista de resultados: kcal, proteína, tiempo y dieta."""
    items = [
        (f"{recipe['kcal']:.0f} kcal", "flame", "orange"),
        (f"P {recipe['protein_g']:.0f} g", "egg", ""),
        (f"{recipe['tiempo_min']} min", "clock", ""),
    ]
    return chips(*items, *([(recipe["dieta"], "leaf", "green")] if diet else []))


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
    legend = " · ".join(f"{k} {v / total * 100:.0f} %" for k, v in kcal_from.items())
    tiles = [
        ("kcal", fmt(values.get("kcal")), "flame", "kcal"),
        ("", fmt(values.get("protein_g"), " g", 1), "egg", "Proteína"),
        ("", fmt(values.get("carbs_g"), " g", 1), "wheat", "Hidratos"),
        ("", fmt(values.get("fat_g"), " g", 1), "droplet", "Grasa"),
        (
            "",
            fmt(values.get("fiber_g"), " g", 1),
            "leaf",
            "Fibra" if values.get("fiber_g") is not None else "Fibra: sin dato",
        ),
    ]
    cells = "".join(
        f'<div class="macro {cls}"><b>{value}</b><small>{icon(name, 13)}{text}</small></div>'
        for cls, value, name, text in tiles
    )
    return (
        f'<div class="macros">{cells}</div><div class="bar">{bar}</div>'
        f'<div class="legend">Valores {label} · energía según macronutriente: {legend}</div>'
    )


def recipe_card(card: dict, *, key: str, expanded: bool = False) -> None:
    items = [(card["dieta"], "leaf", "orange")]
    if card.get("tiempo_min"):
        items.append((f"{card['tiempo_min']} min", "clock", ""))
    items.append((card.get("dificultad", "fácil"), "chef", ""))
    items += [(MEAL_NAMES.get(m, m), "utensils", "green") for m in card.get("comidas", [])]
    items += [(a, "alert", "warn") for a in card.get("alergenos", [])]
    servings = f" · {card['raciones']} raciones" if card.get("raciones", 1) > 1 else ""
    st.markdown(
        f'<div class="card"><h4>{esc(card["titulo"])}{servings}</h4>{chips(*items)}'
        f"{macro_tiles(card['por_racion'])}</div>",
        unsafe_allow_html=True,
    )
    with st.expander("Ingredientes y preparación", icon=":material/restaurant_menu:", expanded=expanded):
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
            x=alt.X("Día:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=13)),
            y=alt.Y("kcal:Q", title="kcal", axis=alt.Axis(labelFontSize=12)),
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
                    f"{short(i['nombre'])} {i['gramos']:.0f} g" for i in meal["ingredientes"]
                )
                macros = f"P {meal['protein_g']:.0f} g · H {meal['carbs_g']:.0f} g · G {meal['fat_g']:.0f} g"
                kcal = f"{meal['kcal']:.0f} kcal"
                tags = chips(
                    (meal["comida"], "utensils", "green"), (kcal, "flame", "orange"), (macros, None, "")
                )
                st.markdown(
                    f'<div class="card">{tags}<h4>{esc(meal["titulo"])}</h4>'
                    f'<div class="muted">{esc(ingredients)}</div></div>',
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
    st.download_button(
        "Descargar lista (.txt)",
        "\n".join(lines),
        "lista_compra_milo.txt",
        icon=":material/download:",
        key=f"dl-{key}",
    )


def search_view(result: dict, *, key: str) -> None:
    for recipe in result["recetas"]:
        status = ""
        if recipe.get("te_falta") is not None:
            missing = ", ".join(short(i) for i in recipe["te_falta"]) or "nada"
            status = f'<div class="status"><span>{icon("cart", 15)}Te falta: {esc(missing)}</span></div>'
        st.markdown(
            f'<div class="card"><h4>{esc(recipe["titulo"])}</h4>{summary_chips(recipe)}{status}</div>',
            unsafe_allow_html=True,
        )


def render_result(result: dict, key: str) -> None:
    kind = result.get("tipo")
    if "error" in result:
        return
    if kind in {"receta", "plato"}:
        recipe_card(result, key=key)
    elif kind == "opciones_sustitucion":
        title = f"Alternativas para {short(result['ingrediente']).lower()}"
        with st.expander(title, icon=":material/swap_horiz:", expanded=True):
            for option in result["opciones"]:
                m = option["receta_por_racion"]
                st.markdown(
                    f"- **{option['alimento']}** ({option['gramos']:.0f} g) → receta: {m['kcal']:.0f} kcal · "
                    f"{m['protein_g']:.0f} g proteína · {m['fat_g']:.0f} g grasa"
                )
    elif kind == "sustitucion":
        st.markdown(
            f'<div class="status"><span>{icon("repeat", 16)}<b>{esc(result["cambio"]["quitar"])}</b>'
            f" → <b>{esc(result['cambio']['poner'])}</b> "
            f"({result['antes_por_racion']['kcal']:.0f} → {result['despues_por_racion']['kcal']:.0f} kcal)</span></div>",
            unsafe_allow_html=True,
        )
        recipe_card(result["receta"], key=key)
    elif kind == "plan":
        with st.expander("Ver el menú completo", icon=":material/calendar_month:", expanded=True):
            plan_view(result, key=key)
        state.plan = result
    elif kind == "lista_compra":
        with st.expander("Lista de la compra", icon=":material/shopping_cart:", expanded=True):
            shopping_view(result, key=key)
    elif kind == "busqueda" and result["recetas"]:
        label = f"{len(result['recetas'])} recetas encontradas"
        with st.expander(label, icon=":material/restaurant:"):
            search_view(result, key=key)


def sources_view(fragments: list[dict], answer: str) -> None:
    cited = cited_numbers(answer)
    label = f"Fragmentos recuperados de ChromaDB ({len(fragments)})"
    with st.expander(label, icon=":material/menu_book:"):
        st.caption(
            "Así funciona el RAG: busco tu pregunta en mis documentos y Gemini responde con estos fragmentos."
        )
        for f in fragments:
            meta = f["metadata"]
            mark = "cited" if f["citation"] in cited else ""
            distance = f" · distancia {f['distance']:.3f}" if "distance" in f else ""
            text = esc(f["text"][:320]) + ("…" if len(f["text"]) > 320 else "")
            st.markdown(
                f'<div class="source {mark}"><b>[{f["citation"]}] {esc(meta["source_id"])}</b> — '
                f'{esc(location(meta))}<span class="muted">{distance}</span><br>{text}</div>',
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
        state.turns.append({"role": "assistant", "content": str(exc), "results": [], "fragments": []})
    except Exception as exc:  # noqa: BLE001 - muestro el problema de forma comprensible
        message = str(exc)
        if "503" in message or "UNAVAILABLE" in message or "429" in message:
            message = "Gemini está saturado en este momento. Espera unos segundos y vuelve a preguntar."
        state.turns.append(
            {
                "role": "assistant",
                "content": f"No he podido responder: {message[:300]}",
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
    st.markdown(CHAT_CSS, unsafe_allow_html=True)
    if state.turns is None:
        try:
            state.turns = restore_turns(load_agent())
        except Exception:  # noqa: BLE001 - sin clave todavía: la conversación empieza vacía
            state.turns = []
    if state.pending:
        question, state.pending = state.pending, None
        ask_milo(question)
    if not state.turns:
        with st.container(key="hero-mascot"):
            st.image(str(MASCOT), width=210)
        st.markdown(
            """<div class="hero"><h1>¡Hola! Soy MILO.<br>¿Qué cocinamos hoy?</h1>
            <p>Dime qué tienes en la nevera, tu objetivo o tus manías con la comida. Busco en mis documentos,
            calculo los macros con datos reales de USDA y recuerdo lo que me cuentas.</p></div>""",
            unsafe_allow_html=True,
        )
        with st.container(key="suggestions"):
            cols = st.columns(2)
            for n, suggestion in enumerate(SUGGESTIONS):
                if cols[n % 2].button(suggestion, key=f"sug{n}", width="stretch"):
                    state.pending = suggestion
                    st.rerun()
    for n, turn in enumerate(state.turns):
        avatar = str(MASCOT) if turn["role"] == "assistant" else ":material/person:"
        with st.chat_message(turn["role"], avatar=avatar):
            st.markdown(turn["content"])
            for m, result in enumerate(turn.get("results", [])):
                render_result(result, key=f"t{n}r{m}")
            if turn.get("fragments"):
                sources_view(turn["fragments"], turn["content"])
    if question := st.chat_input("Escribe a MILO…"):
        ask_milo(question)
        st.rerun()


# ---------------------------------------------------------------- mi nevera

FOOD_OPTIONS = sorted(
    {f.name_es for f in kitchen.catalog.foods.values() if f.nutrients_per_100g.kcal is not None}
)


def page_fridge() -> None:
    page_header(
        "fridge",
        "Mi nevera",
        "Marca lo que tienes y te digo qué recetas puedes preparar y qué te falta. "
        "Es una búsqueda directa en mi recetario, sin IA.",
    )
    chosen = st.multiselect("¿Qué tienes en casa?", FOOD_OPTIONS, placeholder="Busca: pollo, arroz, huevo…")
    c1, c2, c3 = st.columns(3)
    meal = c1.selectbox("Para", ["Cualquier comida", "desayuno", "comida", "cena", "snack"])
    max_kcal = c2.slider("Máximo de kcal por ración", 150, 1200, 1200, 50)
    max_time = c3.slider("Tiempo máximo (min)", 5, 60, 60, 5)
    if not chosen:
        st.info("Añade al menos un ingrediente para empezar.", icon=":material/kitchen:")
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
            f"He descartado {result['descartadas_por_perfil']} recetas por tu perfil "
            f"({describe_profile(state.profile, kitchen.catalog)})."
        )
    if not result["recetas"]:
        st.warning("No encuentro recetas con esos ingredientes y filtros. Prueba a quitar algún filtro.")
    cols = st.columns(3)
    for n, recipe in enumerate(result["recetas"]):
        with cols[n % 3]:
            missing = ", ".join(short(i) for i in recipe["te_falta"]) or "nada"
            have = len(recipe["tienes"])
            st.markdown(
                f'<div class="card"><h4>{esc(recipe["titulo"])}</h4>{summary_chips(recipe, diet=False)}'
                f'<div class="status"><span>{icon("check", 15)}Tienes {have}</span>'
                f"<span>{icon('cart', 15)}Te falta: {esc(missing)}</span></div></div>",
                unsafe_allow_html=True,
            )
            with st.popover("Ver receta", icon=":material/menu_book:", width="stretch"):
                recipe_card(kitchen.view(state.profile, recipe["recipe_id"]), key=f"fr{n}", expanded=True)
    names = ", ".join(short(c).lower() for c in chosen)
    if st.button(f"Pedir a MILO una idea con {names}", type="primary", icon=":material/chat:"):
        state.pending = f"Tengo {names}. ¿Qué me recomiendas cocinar?"
        state.goto = "Chat"
        st.rerun()


# ---------------------------------------------------------------- plan semanal


def page_plan() -> None:
    page_header(
        "calendar",
        "Plan semanal",
        "Genero un menú con recetas compatibles con tu perfil y ajusto las cantidades a tu objetivo de kcal.",
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
        if st.form_submit_button(
            "Generar menú", type="primary", icon=":material/auto_awesome:", width="stretch"
        ):
            result = kitchen.weekly_plan(state.profile, kcal_diarias=kcal, dias=days, comidas=meals)
            if "error" in result:
                st.error(result["error"])
            else:
                state.plan = result
    if state.plan:
        plan_view(state.plan, key="plan")
        st.markdown(
            f'<div class="page-title" style="margin-top:1.5rem"><div class="badge">{icon("cart", 22)}</div>'
            "<h3 style='margin:0;padding:0'>Lista de la compra</h3></div>",
            unsafe_allow_html=True,
        )
        st.write("")
        shopping_view(kitchen.shopping_list(state.plan), key="plan-list")


# ---------------------------------------------------------------- perfil

ALLERGEN_OPTIONS = {v: k for k, v in ALLERGENS_ES.items()}
GOALS = ["Comer más sano", "Mantener peso", "Perder peso", "Ganar masa muscular"]


def page_profile() -> None:
    page_header(
        "user", "Mi perfil", "MILO usa estos datos para filtrar recetas con Python antes de recomendar nada."
    )
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
        if st.form_submit_button("Guardar perfil", type="primary", icon=":material/save:", width="stretch"):
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
            st.success("Perfil guardado. MILO lo tendrá en cuenta en el chat, la nevera y el menú.")
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
    "Chat": (":material/chat_bubble:", page_chat),
    "Mi nevera": (":material/kitchen:", page_fridge),
    "Plan semanal": (":material/calendar_month:", page_plan),
    "Mi perfil": (":material/person:", page_profile),
}

with st.sidebar:
    with st.container(key="side-mascot"):
        st.image(str(MASCOT), width=170)
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
        format_func=lambda p: f"{PAGES[p][0]} {p}",
        label_visibility="collapsed",
    )
    st.markdown(
        f'<div class="profile-box"><b>Tu perfil</b><br>{esc(describe_profile(state.profile, kitchen.catalog))}</div>',
        unsafe_allow_html=True,
    )
    if st.button("Nueva conversación", icon=":material/add_comment:", width="stretch"):
        state.thread_id = uuid.uuid4().hex[:12]
        st.query_params["c"] = state.thread_id
        state.turns, state.plan, state.profile = [], None, UserProfile()
        st.rerun()
    st.caption("Gemini · RAG con ChromaDB · LangGraph  \nDatos: USDA FoodData Central y AESAN (2022).")

PAGES[state.page][1]()
