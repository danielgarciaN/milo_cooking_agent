# MILO — AI Nutrition Chef

Proyecto académico de cocina y nutrición general. La arquitectura separa conocimiento documental (RAG), razonamiento (Gemini) y aritmética nutricional (Python). **Sprint 1 implementa datos y cálculo; todavía no hay agente conversacional ni frontend.**

## Resultado del Sprint 1

- Paquete Python instalable con nueve contratos Pydantic.
- 70 alimentos USDA: 65 Foundation Foods y 5 SR Legacy; 68 tienen energía y macros completos. Los ausentes permanecen como null.
- 12 recetas con pasos específicos, IDs y macros calculados: siete verificadas y cinco pendientes por composición/alérgenos de productos compuestos.
- Descargas reales con URL, fecha, tamaño, SHA-256 y validación de formato. El CSV Foundation de octubre de 2026 carece de dos tablas esenciales y se registra como incompleto.
- Calculadora, ajuste de cantidades y restricciones sin LLM ni API key.
- Extracción de AESAN (19 páginas) y diccionario USDA (17 páginas), con fragmentos y procedencia. El diccionario técnico no completa artificialmente el corpus nutricional.
- Notebook offline ejecutado, 70 tests superados y resultados en `evaluation/results/`.

Progreso y evidencias: [PROJECT_CHECKLIST.md](PROJECT_CHECKLIST.md). Decisiones e incidencias: [docs/SPRINT_LOG.md](docs/SPRINT_LOG.md).

## Instalación

Probado en Windows con Python 3.14.5. El paquete declara Python >=3.11; otras versiones y el extra RAG necesitan verificación antes del despliegue. No se modifica el Python global.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` instala el paquete y herramientas de prueba. `requirements-lock.txt` registra las versiones exactas del entorno probado. Para reproducirlas en un entorno compatible:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

En Linux/macOS, sustituir `.\.venv\Scripts\python.exe` por `.venv/bin/python`. Los CSV/JSON preparados están en el repositorio. Para regenerarlos desde originales, ejecutar desde la raíz:

```powershell
.\.venv\Scripts\python.exe scripts/download_sources.py
.\.venv\Scripts\python.exe scripts/register_sources.py
.\.venv\Scripts\python.exe scripts/build_catalog.py
.\.venv\Scripts\python.exe scripts/prepare_recipes.py
.\.venv\Scripts\python.exe scripts/ingest.py
```

La descarga registra fallos y continúa. `--fallback-dir RUTA` importa archivos locales cuando falla la red, distinguiendo importación de descarga. `--skip-existing` inspecciona archivos presentes sin descargarlos; para registrar procedencia deben existir registros en el manifiesto. PDF, ZIP y fragmentos extraídos están excluidos de Git. Las descargas USDA no requieren API key.

## Uso del núcleo

```python
from milo.models import RecipeIngredient
from milo.repositories.catalog import FoodCatalog, lookup_food
from milo.domain.nutrition import calculate_nutrition

catalog = FoodCatalog.from_csv("data/structured/foods.csv")
food = lookup_food("fdc_2646170", catalog, state="raw")
ingredient = RecipeIngredient(
    ingredient_name=food.name_es, food_id=food.food_id, grams=150, state="raw"
)
result = calculate_nutrition([ingredient], catalog)
print(result.totals.rounded())
print(result.complete, result.approximate, result.missing)
```

| Función | Módulo | Comportamiento |
|---|---|---|
| `lookup_food` | `milo.repositories.catalog` | ID o nombre exacto; error si falta o es ambiguo |
| `calculate_nutrition` | `milo.domain.nutrition` | Suma por gramos y divide entre raciones |
| `calculate_recipe_nutrition` | `milo.domain.nutrition` | Cálculo de una receta |
| `adjust_portions` | `milo.domain.recipes` | Escala uniforme a kcal por ración dentro del factor 0.5–2; valida restricciones |
| `validate_recipe` | `milo.domain.constraints` | Comprueba referencias, estado, nutrientes esenciales, alérgenos y perfil |

`NutritionResult.complete` significa que kcal, proteína, carbohidratos y grasa están completos. La fibra es opcional y se informa si falta. Un cálculo completo **no implica aptitud ante alergias**: consultar también `validate_recipe`. La composición de una marca concreta no se deduce de un registro genérico.

Todas las cifras son aproximadas. Se utiliza `Decimal`, sin redondeos intermedios; `ROUND_HALF_UP` solo para presentación. JSON serializa decimales como cadenas para conservar precisión; los ausentes son `null` en JSON y celdas vacías en CSV. No hay conversiones automáticas entre g, ml, unidades, crudo y cocinado, ni relleno de kcal con la fórmula 4/4/9. Ver [diccionario y transformaciones](docs/data_dictionary.md).

## Pruebas y notebook

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=evaluation/results/pytest.xml
.\.venv\Scripts\python.exe -m ruff check src scripts tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/run_notebook.py
```

Las pruebas matemáticas usan fixtures sintéticas `TEST_ONLY`, nunca incluidas en el catálogo real. Las pruebas de integración comparan valores con los ZIP oficiales, hashes, PDFs y recetas. Si faltan originales, se omiten explícitamente las comprobaciones que los necesitan; descargar las fuentes para reproducir la verificación completa.

Abrir [notebooks/00_sprint1_validation.ipynb](notebooks/00_sprint1_validation.ipynb) con el intérprete de `.venv`. El script lo ejecuta con un kernel local temporal en `storage/`. Sus ocho celdas prueban el núcleo; **no reemplaza las cinco consultas del futuro agente exigidas por el enunciado**.

## Preparación del RAG

La extracción offline genera JSONL por fuente, hash, página y sección. La detección de títulos es heurística: queda pendiente evaluar la calidad semántica de los fragmentos. Los PDF sin texto se señalan para OCR; no hay OCR implementado.

Los adaptadores opcionales de Gemini Embeddings y Chroma están preparados, pero no se han ejecutado contra la API por falta de clave. La instalación del extra RAG tampoco forma parte del entorno verificado de este sprint. Para la siguiente fase:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[rag]"
Copy-Item .env.example .env
# Editar .env localmente: GOOGLE_API_KEY=...
.\.venv\Scripts\python.exe scripts/ingest.py --index
```

`--index` envía texto del corpus a Gemini. Prepara `gemini-embedding-001` a 3072 dimensiones y separa colecciones por modelo/corpus, con IDs estables. Otros modelos o dimensiones se rechazan hasta revisar la integración. El adaptador LangChain diferencia documentos y consultas. No se usan embeddings simulados.

Referencias: [Gemini Embeddings](https://ai.google.dev/gemini-api/docs/embeddings), [integración LangChain](https://docs.langchain.com/oss/python/integrations/embeddings/google_generative_ai), [Chroma](https://docs.langchain.com/oss/python/integrations/vectorstores/chroma).

LangGraph, memoria, prompt final justificado, recuperación evaluada y Streamlit están pendientes. Ver [arquitectura](docs/architecture.md). Los directorios `agent/` y `memory/` documentan su alcance futuro; no cuentan como funciones terminadas.

## Fuentes y límites

`data/sources.json` normaliza fuentes; `data/download_manifest.json` conserva intentos de descarga. `docs/materials/` conserva checklist y fuentes originales; los archivos `*_DRAFT` permanecen intactos. Las recetas son adaptaciones editoriales de MILO, no recetas oficiales USDA.

USDA declara los datos FDC de dominio público/CC0 en su [guía oficial](https://fdc.nal.usda.gov/api-guide/). La reutilización de PDFs e imágenes de terceros necesita revisión antes de redistribuirlos; por ello los originales no se incluyen en Git. El corpus académico todavía está pendiente de cierre.

MILO ofrece información general y no prescribe tratamiento clínico. Los alérgenos conocidos no certifican ausencia de trazas. Ver [límites](docs/safety.md).

Nunca introducir claves en notebooks, commits o mensajes del chat. `.env`, `.venv`, `storage`, PDF/ZIP y secretos Streamlit están ignorados. Git está inicializado localmente; no se ha publicado ni desplegado.
