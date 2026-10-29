# MILO — SPRINT 1: Implementación real de la base del proyecto

He revisado y aprobado tu propuesta arquitectónica para MILO — AI Nutrition Chef.

A partir de ahora quiero que empieces a implementar el proyecto. Ya no estamos únicamente en la fase de diseño.

**Objetivo:** construir el repositorio funcional, preparar los datos iniciales, implementar los contratos y las herramientas nutricionales deterministas, y dejar preparada la ingestión documental.

El proyecto debe seguir cumpliendo el enunciado académico original: Gemini, Gemini Embeddings, ChromaDB, LangGraph, memoria, notebook funcional, documentación y, posteriormente, Streamlit.

## 1. Materiales de entrada

Te proporcionaré el archivo `MILO_FASE1_MATERIALES.zip`.

Descomprímelo, revisa íntegramente su contenido y utiliza sus archivos como material inicial.

Incluye:

- `data/sources.json`
- `data/structured/recipes_DRAFT.json`
- `data/structured/foods_TEMPLATE.csv`
- `data/structured/substitutions_DRAFT.json`
- `docs/INSTRUCCIONES.md`
- `CHECKLIST_FASE1.md`

Estos archivos NO son datasets finales verificados.

No conviertas los borradores en datos definitivos sin revisar su calidad, su procedencia y sus restricciones.

## 2. Crear la estructura real del repositorio

Implementa la estructura modular propuesta anteriormente.

Configura:

- `src/milo/`
- `data/raw/`
- `data/structured/`
- `data/processed/`
- `src/milo/domain/`
- `src/milo/rag/`
- `src/milo/agent/`
- `src/milo/memory/`
- `src/milo/repositories/`
- `notebooks/`
- `tests/`
- `scripts/`
- `docs/`
- `evaluation/`

Crea:

- `pyproject.toml`
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `README.md`

No incluyas claves privadas, datos sensibles ni archivos temporales en Git.

Comprueba que el paquete puede instalarse y que sus módulos pueden importarse.

## 3. Implementar los contratos de datos

Desarrolla modelos Pydantic para:

- `Food`
- `NutrientValues`
- `Recipe`
- `RecipeIngredient`
- `UserProfile`
- `DietaryRestriction`
- `NutritionResult`
- `DataSource`
- `ValidationResult`

Cada alimento debe conservar:

- Identificador interno.
- Nombre en español.
- Nombre original.
- FDC ID cuando proceda.
- Estado de preparación.
- kcal por 100 g.
- Proteínas por 100 g.
- Carbohidratos por 100 g.
- Grasas por 100 g.
- Fibra cuando esté disponible.
- Fuente y versión.
- Estado de validación.

Los valores desconocidos se representarán como `null`, nunca como cero.

Diferencia los pesos crudos de los cocinados.

## 4. Descargar y preparar documentación oficial

Intenta descargar automáticamente los siguientes recursos:

**AESAN:**
https://www.aesan.gob.es/AECOSAN/docs/documentos/nutricion/RECOMENDACIONES_DIETETICAS.pdf

**USDA Foundation Foods CSV ZIP:**
https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2026-10-29.zip

**USDA Field Descriptions:**
https://fdc.nal.usda.gov/docs/Download_Field_Descriptions_Oct2020.pdf

Registra para cada recurso:

- URL.
- Fecha de descarga.
- Tamaño.
- Hash SHA-256.
- Tipo de archivo.
- Estado de descarga.
- Versión o fecha de publicación.
- Condiciones de uso conocidas.

Verifica que cada PDF es válido y que los ZIP pueden abrirse.

Si tu entorno no tiene acceso a Internet, NO simules las descargas. Indícame exactamente qué archivos debo colocar manualmente en `data/raw/`.

## 5. Crear el catálogo nutricional inicial

Utilizando los datos reales de USDA, selecciona como mínimo 50 alimentos útiles para recetas cotidianas.

Prioriza:

- Pollo, pavo, ternera, pescado, huevos y tofu.
- Arroz, pasta, avena, pan, patata y quinoa.
- Leche, yogures y derivados.
- Frutas y verduras.
- Legumbres.
- Aceites y frutos secos.

Relaciona correctamente las tablas de USDA, sus identificadores y los nutrientes.

No asumas que todos los registros de Foundation Foods contienen todos los nutrientes.

Conserva los identificadores originales y utiliza valores nulos cuando falten.

No inventes composición nutricional ni equivalencias.

Crea un CSV final validado y documenta las transformaciones realizadas.

Si no encuentras 50 registros adecuados, informa de la cobertura alcanzada y qué datos adicionales necesitamos.

## 6. Preparar el recetario

Importa los 12 borradores proporcionados.

Para cada receta:

- Completa instrucciones culinarias específicas y coherentes.
- Vincula ingredientes a identificadores reales del catálogo.
- Comprueba estados y cantidades.
- Identifica los alérgenos que puedan deducirse de los ingredientes, dejando pendientes los casos ambiguos.
- Calcula los macros mediante Python.
- Registra las recetas que no puedan validarse.

No declares una receta validada si falta cualquier ingrediente esencial, equivalencia o dato nutricional necesario.

No inventes calorías ni macros.

## 7. Implementar herramientas matemáticas

Desarrolla funciones Python para:

`lookup_food()`

`calculate_nutrition()`

`calculate_recipe_nutrition()`

`adjust_portions()`

`validate_recipe()`

Las calorías y macronutrientes deben calcularse a partir de valores verificados del catálogo.

Implementa una política explícita para datos faltantes, ingredientes compuestos, errores de unidades y restricciones incompatibles.

La salida debe indicar cuándo un cálculo es incompleto o aproximado.

## 8. Pruebas automatizadas

Crea pruebas con pytest para comprobar:

1. Cálculo de nutrientes para 100 g.
2. Escalado a 150 g y 250 g.
3. Suma de varios ingredientes.
4. División entre raciones.
5. Valores nulos y ausencia de datos.
6. Ingrediente inexistente.
7. Diferencia entre crudo y cocinado.
8. Cantidades negativas o inválidas.
9. Restricciones y alérgenos conocidos.
10. Redondeo de resultados.

Ejecuta las pruebas y entrega los resultados reales.

No consideres completada una tarea si su prueba no funciona.

## 9. Preparación del futuro RAG

Prepara el módulo de ingestión:

- Lectura de PDF.
- Extracción de páginas.
- Limpieza básica.
- Segmentación por secciones.
- Metadatos de procedencia.
- Preparación para Gemini Embeddings y ChromaDB.

Si dispones de API key configurada, puedes realizar una prueba de embeddings y recuperación.

Si todavía no está configurada, deja preparada la integración sin inventar resultados.

No es necesario completar el agente LangGraph ni Streamlit en este sprint.

## 10. CHECKLIST OBLIGATORIA

Quiero un archivo permanente en la raíz del repositorio llamado:

`PROJECT_CHECKLIST.md`

Debe contener todas las fases del proyecto, alineadas con la checklist maestra y los requisitos académicos.

Cada tarea tendrá:

- ID.
- Descripción.
- Estado: pendiente, en progreso o completada.
- Evidencia técnica cuando esté completada.
- Archivo o módulo relacionado.
- Prueba que demuestra su funcionamiento.

Utiliza identificadores estables, por ejemplo:

- `1.4` Revisión de arquitectura.
- `2.2` Documentos descargados.
- `2.3` Catálogo nutricional.
- `3.3` Gemini Embeddings.
- `4.4` Calculadora de macros.

NO marques una tarea como completada solo porque has creado un archivo vacío o un esqueleto de función.

Para marcar una tarea como completada, debe existir el resultado esperado y haberse verificado.

Mantén también `docs/SPRINT_LOG.md`, con registro de decisiones, cambios, bloqueos y pruebas realizadas.

## 11. Formato obligatorio al finalizar tu trabajo

Termina tu respuesta con estas secciones:

### A. Trabajo realizado
Qué has implementado realmente.

### B. Checklist actualizada
IDs completados, pendientes y en progreso, indicando las evidencias.

### C. Tests ejecutados
Comandos, cantidad de tests superados y errores encontrados.

### D. Archivos modificados
Rutas reales de los archivos.

### E. Lo que necesito hacer yo
Solo acciones que requieren mi intervención: claves, permisos, descargas bloqueadas o decisiones imprescindibles.

### F. Próximo sprint recomendado
Qué implementarías a continuación y qué criterios permitirán darlo por completado.

## Reglas finales

- Prioriza calidad, reproducibilidad y claridad académica.
- No implementes funcionalidades simuladas presentándolas como funcionales.
- No dejes valores nutricionales inventados para completar tablas.
- No avances a Streamlit antes de tener el núcleo probado.
- No vuelvas a responder únicamente con una propuesta de arquitectura.
- Escribe código, ejecuta pruebas y reporta lo que efectivamente has conseguido.
- Si aparece una limitación, continúa con las demás tareas independientes.
- El objetivo final es alcanzar la máxima calificación posible demostrando técnicamente todo lo desarrollado.

**Empieza ahora el Sprint 1.**