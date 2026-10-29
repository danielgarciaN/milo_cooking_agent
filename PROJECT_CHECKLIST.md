# MILO — Checklist permanente del proyecto

Actualizada: 30/10/2026, Europe/Madrid. IDs estables alineados con `docs/materials/MILO_CHECKLIST_ORIGINAL.md` y el enunciado académico. Estados permitidos: **pendiente**, **en progreso**, **completada**. Existir como archivo o carpeta no demuestra funcionamiento.

La columna «Prueba / cierre» identifica la comprobación realizada para tareas completadas y la comprobación todavía necesaria para las demás. Evidencia común: `evaluation/results/pytest.xml`, `evaluation/results/notebook_execution.json`, informes de datos y `docs/SPRINT_LOG.md`. Las fixtures de tests no cuentan como alimentos reales.

## 1. Diseño y planificación

| ID | Descripción | Estado | Archivo / evidencia técnica | Prueba / cierre |
|---|---|---|---|---|
| 1.1 | Elegir dominio cocina/nutrición | completada | README.md; solicitud del usuario | Revisión del alcance frente al PDF |
| 1.2 | Nombre y personalidad provisional | completada | README.md; docs/architecture.md | MILO y ámbito definidos; personalidad final irá en prompt |
| 1.3 | Registrar solicitud inicial y Sprint 1 | completada | docs/materials/SPRINT1_REQUEST.md | Solicitud contrastada con implementación y checklist |
| 1.4 | Revisar y aprobar arquitectura | completada | docs/architecture.md | Aprobación explícita en solicitud Sprint 1 |
| 1.5 | Aprobar estructura e instalar paquete | completada | pyproject.toml; src/milo/; requirements.txt | Instalación editable; test_all_package_modules_import_without_key |
| 1.6 | Separar MVP y extras | completada | docs/architecture.md | Matriz de fases; agente/frontend expresamente pendientes |
| 1.7 | Contratos y configuración | completada | src/milo/models.py; config.py; .env.example | Tests de cantidades, unidades, nutrientes, restricciones e importación |

## 2. Base de conocimiento

| ID | Descripción | Estado | Archivo / evidencia técnica | Prueba / cierre |
|---|---|---|---|---|
| 2.1 | Localizar fuentes oficiales | completada | data/sources.json; docs/materials/sources_ORIGINAL.json | URLs oficiales contrastadas y recursos descargados |
| 2.2 | Descargar y organizar PDFs y archivos USDA | completada | data/download_manifest.json; data/raw/ | test_source_hashes_and_format; dos PDF válidos; ZIP CRC correcto; CSV octubre incompleto registrado |
| 2.3 | Obtener y normalizar catálogo de >=50 alimentos | completada | data/structured/foods.csv; evaluation/catalog_report.json | 70 alimentos, 65 Foundation, 68 con macros; tests de cobertura y contraste con archivos USDA |
| 2.4 | Recetario completamente validado | en progreso | data/structured/recipes.json; evaluation/recipe_report.json | 12 revisadas/calculadas; 7 verificadas, 5 pendientes de composición/alérgenos |
| 2.5 | Documento de sustituciones verificado | pendiente | data/structured/substitutions_DRAFT.json | Validar alternativas por contexto, IDs y recálculo; no asumir 1:1 |
| 2.6 | Guía de técnicas culinarias | pendiente | scripts/prepare_recipes.py tiene pasos, no guía | Documento sustancial con procedencia y revisión |
| 2.7 | Documentar seguridad y límites | completada | docs/safety.md; docs/data_dictionary.md | Revisión documental; test_known_allergens, test_diet_incompatible_or_unknown |
| 2.8 | Limpiar y normalizar datasets incorporados | completada | repositories/usda.py; scripts/build_catalog.py; prepare_recipes.py | Tests de joins, unidades, ceros/null, duplicados y recetas recalculadas |
| 2.9 | Fuentes, fechas, condiciones de uso y metadatos | completada | data/sources.json; data/download_manifest.json | DataSource valida esquema; SHA-256 real; incertidumbre de reutilización explícita |
| 2.10 | Revisar e importar los 12 borradores sin inventar macros | completada | recipes_DRAFT.json intacto; recipes.json; recipe_nutrition.json | test_recipes_have_specific_steps_and_truthful_status; no implica cierre de 2.4 |
| 2.11 | Corpus sustancial >=3 documentos o ~20 páginas útiles | en progreso | evaluation/ingestion_report.json | AESAN 19 páginas; ampliar corpus; diccionario USDA no cuenta como guía nutricional |

## 3. RAG y Gemini

| ID | Descripción | Estado | Archivo / evidencia técnica | Prueba / cierre |
|---|---|---|---|---|
| 3.1 | Entorno y API key Gemini | en progreso | config.py; .env.example | Entorno offline funciona; falta clave y validar extra rag |
| 3.2 | Ingestión PDF y chunking con procedencia | completada | rag/ingestion.py; scripts/ingest.py; evaluation/ingestion_report.json | test_pdf_ingestion_actual_aesan, test_stable_ids_and_word_bounds; extracción real de 36 páginas |
| 3.3 | Gemini Embeddings reales | pendiente | rag/embeddings.py, adaptador preparado | Ejecutar API y comprobar número/dimensión de vectores; test_missing_key_fails_without_network no sustituye esa prueba |
| 3.4 | ChromaDB indexada | pendiente | rag/retrieval.py, adaptador preparado | Persistir y reabrir colección con embeddings reales |
| 3.5 | Recuperación semántica | pendiente | scripts/ingest.py --index | Consultas reales y resultados trazables; sin resultados simulados |
| 3.6 | Evaluar recuperación | pendiente | evaluation/ | Casos con documentos esperados, cobertura y análisis de fallos |
| 3.7 | System prompt personalizado y justificado | pendiente | docs/safety.md contiene requisitos, no prompt final | Prompt versionado, justificación README y evaluación |
| 3.8 | RAG + Gemini generador | pendiente | src/milo/agent/ reservado | Respuestas coherentes con evidencia y citas comprobables |

## 4. Agente y funciones

| ID | Descripción | Estado | Archivo / evidencia técnica | Prueba / cierre |
|---|---|---|---|---|
| 4.1 | Agente LangGraph | pendiente | agent/__init__.py documenta ausencia | Grafo real ejecutado con rutas y límite de ciclos |
| 4.2 | Memoria conversacional | pendiente | memory/__init__.py documenta ausencia | Referencia al turno previo, perfil y aislamiento de sesiones |
| 4.3 | Clasificador de intenciones | pendiente | docs/architecture.md | Casos de intención combinada, aclaración y límites |
| 4.4 | Calculadora determinista kcal/macros | completada | domain/nutrition.py; domain/recipes.py | Tests 100/150/250 g, suma, raciones, null, estado, redondeo y ajuste |
| 4.5 | Recomendador de recetas | pendiente | catálogo disponible | Recuperar y seleccionar respetando restricciones; sin datos pendientes |
| 4.6 | Planes diarios/semanales | pendiente | diseño en architecture.md | Totales reproducibles, variedad y objetivos imposibles explícitos |
| 4.7 | Restricciones, sustituciones y alergias integradas | en progreso | domain/constraints.py | Restricciones/alérgenos probados; sustituciones y uso por agente pendientes |
| 4.8 | Lista de compra | pendiente | diseño aprobado | Suma por alimento/estado y descuento de existencias compatible |
| 4.9 | Modo nevera | pendiente | diseño aprobado | Recetas por ingredientes disponibles y faltantes explícitos |
| 4.10 | Validar salidas y gestionar errores del sistema | en progreso | modelos, dominio, descargas | Núcleo probado; errores LLM/cuotas/rutas pendientes |

## 5. Frontend y bonus

| ID | Descripción | Estado | Archivo / evidencia técnica | Prueba / cierre |
|---|---|---|---|---|
| 5.1 | Diseñar mascota MILO | pendiente | Sin implementar | Revisión de identidad visual |
| 5.2 | Identidad visual | pendiente | Sin implementar | Sistema visual coherente y accesible |
| 5.3 | Interfaz Streamlit | pendiente | No iniciada en Sprint 1 | Chat funcional conectado al núcleo real |
| 5.4 | Perfil nutricional en interfaz | pendiente | UserProfile disponible | Edición, restricciones y aislamiento de sesiones |
| 5.5 | Visualizar recetas/macros | pendiente | Resultados estructurados disponibles | Mostrar cálculos reales, incompletitud y fuentes |
| 5.6 | Visualizar plan semanal | pendiente | Planificador pendiente | Plan coherente con resultados del dominio |
| 5.7 | Desplegar Streamlit Cloud | pendiente | Sin despliegue | URL pública, secretos y estrategia de persistencia |
| 5.8 | Probar app pública | pendiente | Sin despliegue | Flujo externo completo y sesiones independientes |

## 6. Evaluación y entrega académica

| ID | Descripción | Estado | Archivo / evidencia técnica | Prueba / cierre |
|---|---|---|---|---|
| 6.1 | Notebook académico funcional del agente | en progreso | notebooks/00_sprint1_validation.ipynb | Ocho celdas offline ejecutadas; faltan chat, Gemini, RAG y memoria |
| 6.2 | Cinco consultas con respuestas documentadas | pendiente | Casos propuestos en arquitectura previa | Guardar respuestas reales del agente, fuentes y resultados de tools |
| 6.3 | Probar memoria, recuperación y fundamentación | pendiente | evaluation/ | Evaluación conversacional y de evidencia; sin API aún |
| 6.4 | Probar cálculos nutricionales | completada | tests/; evaluation/results/pytest.xml | 70 tests superados en ejecución final; incluye datos reales y fallos controlados |
| 6.5 | README de instalación y ejecución | completada | README.md; requirements-lock.txt | Comandos de instalación, datos, tests y notebook ejecutados |
| 6.6 | Arquitectura y decisiones técnicas | completada | docs/architecture.md; data_dictionary.md; SPRINT_LOG.md | Revisión frente a solicitud, código y evidencias |
| 6.7 | Presentación 5–10 minutos | pendiente | Sin preparar | Guion, decisiones y demo dentro del tiempo |
| 6.8 | Ensayar demo en vivo | pendiente | Sin agente final | Ejecución desde entorno limpio y contingencias documentadas |
| 6.9 | Revisar rúbrica completa | en progreso | Esta checklist y PDF académico | Falta demostrar agente, memoria, embeddings, corpus y consultas finales |

## Regla de actualización

Tras cada sprint registrar ejecución real, incidencias y resultado en `docs/SPRINT_LOG.md`. Actualizar IDs existentes sin renumerar. Un archivo vacío, adaptador no ejecutado, respuesta de ejemplo inventada o prueba omitida no justifican completar una tarea. Las tareas clínicas/IA y el bonus no están implícitamente aprobados como terminados por disponer del núcleo.
