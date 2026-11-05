# MILO — Checklist del proyecto

Actualizado el 06/11/2026. Solo marco ✅ lo que he comprobado ejecutándolo. ⏳ = depende de una acción externa.

## Requisitos del enunciado

| Requisito | Estado | Dónde se comprueba |
|---|---|---|
| Agente experto en un dominio (cocina y nutrición) | ✅ | README §1, notebook §1 |
| Base vectorial con ≥ 3 documentos / ~20 páginas | ✅ | 3 documentos, 75 fragmentos (~30 páginas) · notebook §3–4 |
| Indexados en ChromaDB con Gemini Embeddings | ✅ | `gemini-embedding-001`, `storage/chroma` · notebook §5–6 |
| Colección verificada con consultas de prueba antes del agente | ✅ | Notebook §7 (aserciones) · `tests/test_rag.py --live` |
| Respuestas con RAG + Gemini | ✅ | Notebook §8, citas [n] marcadas con ★ |
| System prompt personalizado | ✅ | `src/milo/prompts/system.md` |
| System prompt justificado en el README | ✅ | README §6 |
| Agente en LangGraph que combina RAG y Gemini | ✅ | `src/milo/agent.py` · notebook §9 |
| Memoria de conversación | ✅ | `SqliteSaver` · notebook §10 (incluye reinicio y aislamiento) |
| Ejemplo de pregunta que referencia una respuesta anterior | ✅ | "Hazme la receta anterior para 2 personas" · "lista de la compra de ese menú" |
| Celda interactiva en el notebook | ✅ | Notebook §11, última celda de código |
| ≥ 5 preguntas de ejemplo documentadas | ✅ | Notebook §11: 6 consultas (+ 4 de memoria) |
| README: dominio, instalación, ejecución, prompt, requisitos | ✅ | `README.md` |
| Presentación de 5–10 min con demo | ✅ preparada | `presentacion/MILO_presentacion.html` + `presentacion/GUION.md` |
| Bonus: interfaz Streamlit | ✅ | `app.py` probado en navegador (chat, nevera, plan, perfil) |
| Bonus: despliegue público en Streamlit Cloud | ⏳ | Requiere subir el repositorio a GitHub y conectar la cuenta de Streamlit (ver `ENTREGA_FINAL.md`) |

## A. Auditoría y simplificación

| Tarea | Estado | Nota |
|---|---|---|
| Inspeccionar el repositorio y ejecutar las pruebas | ✅ | 82 pruebas pasaban al empezar; RAG real comprobado |
| Punto de recuperación antes de limpiar | ✅ | Etiqueta git `antes-entrega-final` + zip `../milo_backup_antes_entrega_2026-11-05.zip` |
| Eliminar informes y archivos históricos | ✅ | `storage/archivado`, `evaluation/`, borradores `*_DRAFT`, `recipe_nutrition.json`, `verify.py` |
| Eliminar el repositorio anidado `milo_cooking_agent/` | ✅ | Solo contenía la licencia, que he movido a la raíz |
| Fusionar módulos | ✅ | `catalog.py` → `nutrition.py`; `prepare_documents.py` → `prepare_recipes.py` |
| Datos en pocas carpetas | ✅ | `data/documents`, `data/foods.csv`, `data/recipes.json`, `data/usda/` |
| Conservar fuentes y trazabilidad USDA | ✅ | `data/sources.json` + selecciones; `foods.csv` se regenera idéntico byte a byte |

## B. Datos y documentación

| Tarea | Estado | Nota |
|---|---|---|
| Tres documentos revisados | ✅ | AESAN (PDF oficial), recetario y técnicas (propios, con referencias) |
| 70 alimentos USDA verificados | ✅ | Comparación con los ZIP oficiales en `tests/test_data_pipeline.py` |
| Recetas pendientes corregidas | ✅ | Las 5 pendientes usaban productos comerciales; ahora avisan de revisar la etiqueta y se bloquean si hay alergias |
| Recetario ampliado | ✅ | 28 recetas (antes 12), todas verificadas, con tipo de comida y dificultad |
| Limitaciones del catálogo documentadas | ✅ | README §11 |

## C. RAG

| Tarea | Estado | Nota |
|---|---|---|
| Lectura y extracción real de PDF/Markdown | ✅ | Notebook §3 |
| Limpieza (guiones, ligadura "ﬁ") y omisión de páginas sin contenido | ✅ | Páginas 1, 2 y 19 del PDF |
| Chunking con procedencia (documento, página/sección) | ✅ | Notebook §4 |
| Embeddings Gemini reales | ✅ | Notebook §5 (similitud coseno) |
| ChromaDB persistente y reconstruible | ✅ | `python scripts/build_index.py --rebuild` |
| Índice automático si falta (para Streamlit Cloud) | ✅ | `NutritionRAG(build_if_missing=True)` |
| Recuperación relevante con fuentes | ✅ | Notebook §7 y 5 tests `--live` |
| Respuestas fundamentadas con citas | ✅ | Notebook §8 |

## D. LangGraph y memoria

| Tarea | Estado | Nota |
|---|---|---|
| Grafo sencillo y explicable | ✅ | `recuperar → milo ⇄ herramientas` |
| 8 herramientas Python integradas | ✅ | Probadas con modelo simulado (`tests/test_agent.py`) y con Gemini real |
| Errores de herramientas devueltos a Gemini | ✅ | `ToolNode(handle_tool_errors=True)` + test |
| Memoria entre turnos | ✅ | Notebook §10 |
| Persistencia entre reinicios | ✅ | `storage/memoria.sqlite`, demostrado con un agente nuevo |
| Aislamiento de conversaciones | ✅ | Test y notebook §10 |
| Robustez ante saturación de Gemini (503) | ✅ | Reintentos + modelo de respaldo `gemini-3.1-flash-lite` |

## E. Funciones de cocina

| Función | Estado |
|---|---|
| Recomendar recetas y buscar por ingredientes (Mi nevera) | ✅ |
| Calcular calorías y macros (deterministas) | ✅ |
| Ajustar a kcal objetivo y a varias raciones | ✅ |
| Sustituir ingredientes y recalcular | ✅ |
| Respetar dieta, alergias, intolerancias y alimentos que no gustan | ✅ |
| Plan de 1–7 días con totales diarios | ✅ |
| Lista de la compra por categorías | ✅ |
| Recordar preferencias (perfil) | ✅ |

## F. Frontend

| Tarea | Estado |
|---|---|
| Mascota oficial y paleta naranja-crema | ✅ |
| Inicio con bienvenida y sugerencias | ✅ |
| Chat con fichas calculadas y fragmentos de ChromaDB | ✅ |
| Mi nevera, Plan semanal (gráfico + lista descargable) y Mi perfil | ✅ |
| Lógica importada del núcleo (sin duplicar el agente) | ✅ |
| Errores comprensibles | ✅ |
| Probado localmente en navegador | ✅ |
| Despliegue público | ⏳ |

## G–H. Documentación y validación final

| Tarea | Estado | Resultado |
|---|---|---|
| Notebook final ejecutado de principio a fin | ✅ | `python scripts/run_notebook.py` → 0 errores |
| Pruebas sin API | ✅ | `python -m pytest` → 92 passed |
| Pruebas con Gemini real | ✅ | `python -m pytest --live` → 98 passed |
| Linter | ✅ | `ruff check` sin avisos |
| Sin claves expuestas | ✅ | `.env` en `.gitignore`; búsqueda de la clave en archivos versionables sin resultados |
| README, manual, checklist y guía de entrega | ✅ | Raíz del proyecto |
| Presentación, guion y preguntas del profesor | ✅ | `presentacion/` |
| Ensayar la demo | ⏳ | Tarea mía antes de la defensa |
