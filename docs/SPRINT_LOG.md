# MILO — Registro de sprints

## Sprint 1 — 30/10/2026 (Europe/Madrid)

Solicitud: `docs/materials/SPRINT1_REQUEST.md`. Arquitectura aprobada; implementar base, datos reales, contratos, herramientas deterministas, pruebas e ingestión. No implementar aún LangGraph completo ni Streamlit.

### Materiales y fuentes

- Revisados íntegramente los seis archivos de `MILO_FASE1_MATERIALES.zip`, checklist maestra, PDF de campos USDA y estructura del ZIP aportado. Los borradores originales se conservan sin elevar su estado a verificado.
- Descargados AESAN (PDF 19 páginas), diccionario USDA (PDF 17 páginas) y Foundation CSV octubre 2026. Hashes/tamaños/fechas/HTTP en `data/download_manifest.json`; esquema normalizado en `data/sources.json`.
- Incidencia: el CSV octubre abre y pasa CRC, pero no incluye `food.csv` ni `food_nutrient.csv`. El ZIP aportado coincide con la descarga. Estado `incomplete_archive`; no se usa para calcular.
- Una URL tentativa de abril terminada en `2026-04-23` devolvió HTTP 404. El enlace oficial correcto `2026-04-30` se descargó y contiene las tablas. El intento fallido queda registrado.
- Descargado JSON oficial octubre 2026 para revisar cobertura y actualizar cuatro registros completos (pan, tortilla y dos pastas). Descargado SR Legacy 2018 para cinco alimentos adicionales con IDs y versión propios. No se mezclan valores entre alimentos.
- Resultado: 70 alimentos; 65 Foundation, 5 SR Legacy; 68 con macros completos. Los aceites Foundation 748608 y 1750349 conservan macros null; se ofrecen aceites SR como alimentos distintos.

### Implementación y decisiones

- Paquete instalable en `.venv`, Python 3.14.5. Nueve contratos Pydantic más contrato de fragmentos PDF. Imports sin clave y dependencias opcionales diferidas.
- Cálculos Decimal, sin aritmética LLM. Ausentes propagados, desconocidos explícitos, estados y unidades incompatibles rechazados. Redondeo solo en presentación. Ajuste uniforme con límites y validación de perfil.
- 12 recetas con instrucciones específicas, IDs y cantidades por estado. Frutos rojos concretados 50/50; pavo concretado en picado cocinado. Sin rendimientos inventados. Temperaturas contrastadas con FoodSafety.gov; sin pruebas físicas de cocina.
- Siete recetas verificadas; cinco pendientes por composición/alérgenos de productos compuestos. Doce estimaciones de kcal/macros completas; fibra ausente cuando no se publica. Se retiran etiquetas nutricionales/dietéticas no demostradas de borradores.
- Ingestión PDF real por páginas/secciones, metadatos y hash; 129 fragmentos AESAN y 20 del diccionario técnico. La granularidad de títulos es heurística y se evaluará con retrieval. No se considera cerrado el corpus académico.
- Adaptadores Gemini/Chroma preparados, sin llamadas reales ni vectores ficticios. Falta API key. El extra RAG no está instalado en el entorno verificado; se probará en Sprint 2.
- Git inicializado localmente; sin commits, remoto, publicación ni despliegue. `.env`, temporales, originales y almacenamiento privado ignorados.

### Pruebas e incidencias de ejecución

1. Instalación editable `python -m pip install -e ".[dev]"`: correcta en el entorno local.
2. Scripts `register_sources.py`, `build_catalog.py`, `prepare_recipes.py` e `ingest.py`: ejecutados con resultados reales y reportes guardados.
3. Primera suite: 64 tests superados. Ruff señaló 14 incidencias de estilo/manejo de excepciones; corregidas. Se añadieron seis pruebas independientes del importador (joins, prioridad energética, null/cero, unidades, duplicados, descripción cambiada).
4. Suite ampliada: 70 tests superados, cero fallos y cero omitidos con las fuentes presentes. XML en `evaluation/results/pytest.xml`. Último resultado definitivo reflejado en `evaluation/results/verification.json`.
5. `ruff check src scripts tests`: correcto tras correcciones y formato.
6. `pip check`: sin dependencias rotas.
7. Notebook `00_sprint1_validation.ipynb`: ocho celdas de código ejecutadas, cero errores. Informe en `evaluation/results/notebook_execution.json`; no es el notebook final del agente.
8. Se añadió `fonttools` tras avisos de extracción de fuentes tipográficas AESAN; la extracción posterior se ejecuta sin esos avisos.
9. Jupyter en Windows emitió avisos del selector de eventos y transporte local TCP; no interrumpieron la ejecución. El kernel es temporal y usa el intérprete del proyecto.
10. La auditoría final detectó tildes sustituidas por `?` al generar textos mediante la entrada estándar de PowerShell. Se corrigieron selecciones y notebook desde UTF-8, se regeneraron los resultados y se añadió una comprobación de integridad de nombres en el test de catálogo. No afectó a IDs ni valores numéricos.
11. Regeneración determinista contrastada por SHA-256 en `evaluation/results/reproducibility.json`; originales de los seis materiales preservados y comparados byte a byte en `evaluation/materials_audit.json`.

### Pendientes y próximos criterios

- Gemini: el usuario debe configurar localmente una clave; no enviarla por chat. Criterio: embeddings reales, persistencia Chroma y recuperación reproducible con resultados guardados.
- Composición/alérgenos: revisar productos concretos o adaptar las cinco recetas con ingredientes completamente caracterizados. No requiere detener el trabajo restante ni obliga al usuario a aprobar un dato inventado.
- Corpus: ampliar conocimiento culinario/nutricional sustancial y revisar condiciones de reutilización antes del despliegue. El diccionario USDA no sustituye ese contenido.
- Sustituciones: los cuatro borradores son relaciones orientativas, sin equivalencias 1:1. Skyr/yogur de soja no incorporados; módulo de sustitución pendiente.
- Agente, memoria, prompt final, cinco consultas académicas, planificación y frontend siguen pendientes según IDs de PROJECT_CHECKLIST.md.
