# MILO — Mi checklist principal

Actualización: 30/10/2026. Conservo los IDs anteriores y agrupo tareas relacionadas para reducir el seguimiento duplicado. Uso **completada**, **en progreso** y **pendiente**. Solo cierro tareas con una comprobación real. La documentación histórica permanece archivada en `storage/archivado`.

## 1. Diseño y organización

| IDs | Tarea | Estado | Evidencia |
|---|---|---|---|
| 1.1–1.4 | Dominio, nombre MILO, alcance y arquitectura | completada | README y solicitudes aprobadas; cocina y educación general |
| 1.5 | Simplificar e instalar el paquete | completada | Módulos agrupados, referencias actualizadas, copia verificada y tests conservados |
| 1.6 | Separar núcleo y ampliaciones | completada | README; frontend y extras siguen pendientes |
| 1.7 | Contratos y configuración privada | completada | `models.py`, `config.py`; validación y carga del `.env` raíz |

## 2. Datos y documentos

| ID | Tarea | Estado | Evidencia |
|---|---|---|---|
| 2.1–2.2 | Fuentes oficiales y descargas | completada | `data/sources.json`; hashes y CRC; incidencia del CSV de octubre conservada |
| 2.3 | Catálogo de al menos 50 alimentos | completada | 70 alimentos, 68 con macros completos; contraste contra archivos USDA |
| 2.4 | Revisar todo el recetario | en progreso | Siete recetas verificadas y cinco pendientes de composición/alérgenos |
| 2.5 | Sustituciones verificadas | en progreso | Guía documental contrastada; equivalencias y sustituciones automáticas pendientes |
| 2.6 | Guía de técnicas culinarias | completada | `data/documents/tecnicas_y_sustituciones.md`; referencias y límites explícitos |
| 2.7–2.9 | Seguridad, transformaciones y procedencia | completada | README, contratos, fuentes e intentos de descarga en un solo registro |
| 2.10 | Importar los doce borradores sin inventar macros | completada | Borradores conservados; cálculos contrastados por tests |
| 2.11 | Corpus documental sustancial | completada | AESAN, recetario revisado y técnicas: tres documentos, 58 fragmentos |

## 3. RAG y Gemini

| ID | Tarea | Estado | Evidencia |
|---|---|---|---|
| 3.1 | Configurar API y entorno | completada | Clave privada leída y generación real con `gemini-3.5-flash-lite` |
| 3.2 | Extraer y dividir documentos | completada | PDF de 19 páginas y Markdown; metadatos por página/sección y hash |
| 3.3 | Embeddings reales de Gemini | completada | Vector real de 3072 dimensiones; `gemini-embedding-001` |
| 3.4 | Persistencia en ChromaDB | completada | 58 vectores guardados y colección reabierta |
| 3.5 | Recuperación semántica real | completada | Consultas sobre dieta, pollo/arroz, tortilla y sustituciones |
| 3.6 | Evaluar recuperación | completada | Cinco casos live superados; fuente/sección esperada recuperada y citas existentes; muestra limitada |
| 3.7 | Prompt personalizado y citas | completada | `rag.py`; justificación en README; pruebas de citas inexistentes |
| 3.8 | Generación RAG con Gemini | completada | Cinco respuestas reales con fragmentos y citas en la demostración |

## 4. Agente y memoria

| ID | Tarea | Estado | Evidencia |
|---|---|---|---|
| 4.1 | Agente LangGraph sencillo | completada | Cuatro nodos ejecutados con Gemini, Chroma y calculadora |
| 4.2 | Memoria conversacional | completada | Referencia a receta anterior y ajuste a 600 kcal conservados entre turnos; aislamiento probado |
| 4.3 | Interpretar intenciones | en progreso | Receta, nutrientes y ajuste comprobados; ampliar casos ambiguos y adversarios |
| 4.4 | Calculadora determinista | completada | Cálculo, raciones, estados, null y escalado probados |
| 4.5 | Recomendar recetas revisadas | completada | Recuperación documental y validación Python antes de presentar la ficha |
| 4.6 | Planes diarios/semanales | pendiente | Fuera de esta fase |
| 4.7 | Restricciones, alergias y sustituciones | en progreso | Perfil explícito y bloqueo determinista probados; sustitución automática pendiente |
| 4.8–4.9 | Lista de compra y modo nevera | pendiente | Fuera de esta fase |
| 4.10 | Validar salidas y gestionar errores | en progreso | Contratos, citas, recetas pendientes y errores de API; falta evaluación adversaria amplia |

## 5. Interfaz y bonus

| IDs | Tarea | Estado | Criterio de cierre |
|---|---|---|---|
| 5.1–5.2 | Mascota e identidad visual | pendiente | Revisar el diseño cuando se inicie la interfaz |
| 5.3–5.6 | Streamlit, perfil, recetas y planes | pendiente | Conectar y comprobar flujos con el mismo núcleo; no iniciado por indicación expresa |
| 5.7–5.8 | Despliegue y prueba pública | pendiente | Publicación y comprobación de sesiones/secretos |

## 6. Evaluación y presentación

| ID | Tarea | Estado | Evidencia o siguiente comprobación |
|---|---|---|---|
| 6.1 | Notebook académico principal | completada | Diez secciones y diez celdas de código ejecutadas en orden; cero errores y salidas reales guardadas |
| 6.2 | Cinco consultas documentadas | completada | Cinco respuestas del agente en el notebook; fuentes esperadas recuperadas en 5/5 casos |
| 6.3 | Evaluar memoria, recuperación y fundamentación | completada | Memoria real, aislamiento y seis tests live; revisión de las cinco respuestas frente a sus fragmentos; alcance de muestra explícito |
| 6.4 | Pruebas de cálculo y controles | completada | 88 pruebas superadas con --live: 82 locales y seis reales; conservo las 70 originales |
| 6.5–6.6 | README, instalación y decisiones | completada | Documentación en primera persona, comandos y límites del sistema |
| 6.7 | Presentación de 5–10 minutos | pendiente | Preparar y ensayar el discurso |
| 6.8 | Ensayo de demostración | pendiente | Ensayar desde un entorno limpio y comprobar contingencias de red/cuota |
| 6.9 | Revisión final de la rúbrica | en progreso | RAG, agente y memoria implementados; presentación y entrega final pendientes |

No marco completada la validación de cinco recetas pendientes, la sustitución automática, el frontend ni la persistencia de conversaciones tras reiniciar. Las respuestas del modelo pueden variar; los resultados de una muestra pequeña no garantizan todos los casos.
