# MILO — Checklist maestra del proyecto

Actualización inicial: 29/10/2026. Marcar [x] solo después de verificar el entregable.

## 1. Diseño y planificación
- [x] Elegir dominio: cocina y nutrición
- [x] Definir nombre y personalidad provisional de MILO
- [x] Enviar el primer prompt al desarrollador
- [ ] Revisar arquitectura propuesta
- [ ] Aprobar estructura del repositorio
- [ ] Definir alcance MVP y extras

## 2. Base de conocimiento
- [x] Localizar fuentes nutricionales oficiales
- [ ] Descargar y organizar PDFs de nutrición
- [ ] Obtener y normalizar base de alimentos/macros
- [ ] Crear recetario estructurado
- [ ] Crear documento de sustituciones
- [ ] Preparar guía de técnicas culinarias
- [ ] Documentar seguridad y límites nutricionales
- [ ] Limpiar y normalizar datasets
- [ ] Añadir fuentes, licencias, fechas y metadatos

## 3. RAG y Gemini
- [ ] Configurar entorno y API key
- [ ] Implementar ingesta y chunking
- [ ] Crear Gemini Embeddings
- [ ] Crear ChromaDB
- [ ] Implementar recuperación semántica
- [ ] Evaluar recuperación con preguntas y documentos esperados
- [ ] Crear y justificar system prompt
- [ ] Conectar recuperación con Gemini

## 4. Agente y funciones
- [ ] Crear agente LangGraph
- [ ] Implementar memoria conversacional
- [ ] Crear clasificador de intenciones
- [ ] Crear calculadora determinista kcal/macros
- [ ] Crear recomendador de recetas
- [ ] Crear generador de planes semanales
- [ ] Implementar restricciones, sustituciones y alergias
- [ ] Generar lista de la compra
- [ ] Implementar modo nevera
- [ ] Validar salidas y gestionar errores

## 5. Frontend y bonus
- [ ] Diseñar mascota de MILO
- [ ] Crear identidad visual
- [ ] Construir interfaz Streamlit
- [ ] Crear perfil nutricional
- [ ] Visualizar recetas y macros
- [ ] Visualizar plan semanal
- [ ] Desplegar en Streamlit Cloud
- [ ] Probar app pública

## 6. Evaluación y entrega
- [ ] Preparar notebook funcional
- [ ] Documentar mínimo cinco consultas y respuestas
- [ ] Probar memoria, retrieval y groundedness
- [ ] Probar cálculos nutricionales
- [ ] Crear README completo
- [ ] Documentar arquitectura y decisiones técnicas
- [ ] Preparar presentación 5–10 min
- [ ] Ensayar demo en vivo
- [ ] Revisar rúbrica completa

## Fuentes identificadas (todavía no descargadas ni incorporadas al RAG)
- AESAN: https://www.aesan.gob.es/actualidad/publicaciones-nutricion/recomendaciones-dieteticas-saludables-y-sostenibles-complementadas-con-recomendaciones-de-actividad-fisica-para-la-poblacion-espanola
- OMS: https://www.who.int/news-room/fact-sheets/detail/healthy-diet
- USDA FoodData Central descargas: https://fdc.nal.usda.gov/download-datasets/
- USDA FoodData Central API/licencia: https://fdc.nal.usda.gov/api-guide/
- AESAN BEDCA: https://aesan.gob.es/datos-abiertos/alimentos-y-bebidas
- Harvard Healthy Eating Plate: https://nutritionsource.hsph.harvard.edu/healthy-eating-plate/
- AESAN higiene alimentos: https://www.aesan.gob.es/es/seguridad-alimentaria/higiene-alimentos
