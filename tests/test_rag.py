import re
from types import SimpleNamespace

import pytest

from milo.config import Settings
from milo.rag import NutritionRAG, collection_name, load_documents


def test_corpus_is_documentary_and_reviewed():
    chunks = load_documents()
    assert {c.source_id for c in chunks} == {"AESAN_2022", "MILO_RECETAS", "MILO_TECNICAS"}
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    recipes = [c for c in chunks if c.source_id == "MILO_RECETAS"]
    assert any("r001" in c.section for c in recipes)
    assert not any("r004" in c.section for c in recipes)  # Producto pendiente de revisión.
    for sid in {c.source_id for c in chunks}:
        assert sum(len(c.text.split()) for c in chunks if c.source_id == sid) > 500


def test_collection_changes_with_document_or_model():
    chunks = load_documents()
    settings = Settings(_env_file=None)
    original = collection_name(chunks, settings)
    assert original == collection_name(list(reversed(chunks)), settings)
    assert original != collection_name(chunks[:-1], settings)
    assert original != collection_name(chunks, settings.model_copy(update={"embedding_model": "other"}))


@pytest.mark.parametrize("answer", ["Sin cita", "Dato inventado [99]", ""])
def test_rejects_invalid_citations(answer):
    # Doble explícito de unidad; no se presenta como prueba de Gemini.
    rag = object.__new__(NutritionRAG)
    rag.model = SimpleNamespace(invoke=lambda _: SimpleNamespace(content=answer))
    with pytest.raises(ValueError, match="citas"):
        rag.generate("Pregunta", [{"citation": 1, "text": "Evidencia", "metadata": {"source_id": "TEST"}}])


@pytest.mark.live
@pytest.mark.parametrize(
    "question,source,section",
    [
        ("¿Qué recomendaciones nutricionales hay para una dieta equilibrada?", "AESAN_2022", None),
        ("Recomiéndame una receta sencilla con pollo y arroz.", "MILO_RECETAS", "r001"),
        ("¿Cómo preparo una tortilla de espinacas?", "MILO_RECETAS", "r002"),
        ("¿Puedo cambiar arroz seco por el mismo peso de patata cruda?", "MILO_TECNICAS", None),
        ("¿Es un yogur sin lactosa apropiado para una alergia a la leche?", "MILO_TECNICAS", None),
    ],
)
def test_real_retrieval_and_generation(question, source, section):
    result = NutritionRAG().ask(question)
    assert any(
        f["metadata"]["source_id"] == source and (section is None or section in f["metadata"]["section"])
        for f in result.fragments
    )
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", result.answer)}
    assert cited and cited <= {f["citation"] for f in result.fragments}
