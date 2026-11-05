# Manual del proyecto MILO — AI Nutrition Chef

Este es el manual completo de MILO. Explica qué es, dónde está cada cosa, cómo funcionan sus piezas por dentro, cómo
se ejecuta, cómo se modifica y cómo defenderlo en la presentación. Lo he escrito para que se entienda sin haber
desarrollado nunca un agente de inteligencia artificial.

**Índice**

1. [Qué es MILO](#1-qué-es-milo)
2. [Estructura del repositorio](#2-estructura-del-repositorio)
3. [Los datos: carpeta `data/`](#3-los-datos-carpeta-data)
4. [Los scripts: carpeta `scripts/`](#4-los-scripts-carpeta-scripts)
5. [El código: carpeta `src/milo/`](#5-el-código-carpeta-srcmilo)
6. [El system prompt y los demás prompts](#6-el-system-prompt-y-los-demás-prompts)
7. [El RAG paso a paso](#7-el-rag-paso-a-paso)
8. [LangGraph: el agente](#8-langgraph-el-agente)
9. [Las herramientas del agente](#9-las-herramientas-del-agente)
10. [La memoria](#10-la-memoria)
11. [La API de Gemini](#11-la-api-de-gemini)
12. [La web con Streamlit](#12-la-web-con-streamlit)
13. [Las pruebas: carpeta `tests/`](#13-las-pruebas-carpeta-tests)
14. [La carpeta `storage/`](#14-la-carpeta-storage)
15. [Cómo ejecutar MILO desde cero](#15-cómo-ejecutar-milo-desde-cero)
16. [Cómo modificar el proyecto](#16-cómo-modificar-el-proyecto)
17. [Problemas habituales](#17-problemas-habituales)
18. [Guía para defender el proyecto](#18-guía-para-defender-el-proyecto)
19. [Glosario](#19-glosario)

---

## 1. Qué es MILO

**MILO** es un asistente de cocina y nutrición con personalidad de pequeño chef. Su mascota es una criatura con gorro de
cocinero, delantal crema y cuchara de madera (`assets/milo.png`).

### Qué problema resuelve

Mucha gente no sabe qué cocinar con lo que tiene en la nevera, cómo ajustar una receta a unas calorías concretas o cómo
organizar las comidas de la semana. MILO ayuda con esas decisiones.

### Qué puede hacer

| Le pido… | MILO… |
|---|---|
| "¿Qué recomienda la documentación sobre alimentación equilibrada?" | Busca en la guía oficial de AESAN y responde citando la página |
| "Tengo pollo, arroz y huevos. Quiero una cena de 800 kcal" | Busca recetas con esos ingredientes, escala una a 800 kcal y calcula sus macros |
| "No tengo aguacate, ¿por qué lo cambio?" | Propone alternativas del catálogo y recalcula la receta |
| "Hazme un menú de 3 días de 2.500 kcal" y "la lista de la compra" | Crea el menú y suma los ingredientes por categorías |
| "Soy vegetariano y no me gusta el tomate" | Lo guarda y no vuelve a recomendar recetas incompatibles |
| "Hazme la receta anterior para 2 personas" | Recuerda cuál era y duplica las cantidades |

### Tecnologías

| Tecnología | Para qué la uso |
|---|---|
| **Python** | Todo el proyecto |
| **Google Gemini** | El modelo de lenguaje que redacta las respuestas y decide qué herramienta usar |
| **Gemini Embeddings** | Convertir textos en vectores para buscar por significado |
| **ChromaDB** | Guardar esos vectores y buscar los fragmentos más parecidos a una pregunta |
| **LangChain** | Piezas comunes para hablar con Gemini, con Chroma y para definir herramientas |
| **LangGraph** | Organizar el agente como un grafo de pasos y darle memoria |
| **Streamlit** | La aplicación web |
| **Jupyter Notebook** | La demostración paso a paso para el profesor |
| **USDA FoodData Central** | Los valores nutricionales reales de los alimentos |

### Qué significa que MILO sea un agente

Un **chatbot normal** recibe una pregunta y responde con lo que "sabe" el modelo. Si le preguntas cuántas calorías
tiene un plato, se las inventa de forma aproximada.

Un **agente** puede **decidir hacer cosas** antes de responder. MILO:

1. Busca información en sus propios documentos (RAG).
2. Decide si necesita una herramienta (por ejemplo, la calculadora de macros) y la ejecuta.
3. Lee el resultado y, si hace falta, usa otra herramienta.
4. Solo entonces redacta la respuesta, usando los datos que ha obtenido.
5. Recuerda la conversación para el siguiente mensaje.

Ejemplo sencillo: si pregunto "¿cuántas calorías tiene el bowl de pollo para 2 personas?", un chatbot calcularía "a
ojo". MILO llama a la herramienta `ver_receta` con `raciones=2`, Python multiplica los gramos y suma los valores USDA, y
Gemini me explica el resultado exacto.

---

## 2. Estructura del repositorio

Esta es la estructura real (sin `.venv/`, `.git/` y cachés de Python):

```text
milo_cooking_agent/
├── MILO_Proyecto_Final.ipynb      ← notebook de entrega
├── app.py                         ← aplicación web Streamlit
├── README.md                      ← resumen de entrega (instalación, RAG, justificación del prompt)
├── MANUAL_DEL_PROYECTO.md         ← este manual
├── PROJECT_CHECKLIST.md           ← requisitos y su estado verificado
├── ENTREGA_FINAL.md               ← qué entregar y cómo comprobarlo
├── LICENSE                        ← licencia MIT del código
├── requirements.txt               ← librerías necesarias
├── requirements-lock.txt          ← versiones exactas con las que lo he probado
├── pyproject.toml                 ← define el paquete "milo" y la configuración de pytest y ruff
├── .env.example                   ← plantilla de configuración (sin clave)
├── .env                           ← MI clave de Gemini (privado, no se sube a GitHub)
├── .gitignore / .gitattributes    ← qué no se sube a git y cómo tratar los finales de línea
├── .streamlit/config.toml         ← colores y tipografías de la app
├── assets/
│   ├── milo.png                   ← mascota oficial (PNG transparente, 1254×1254)
│   └── milo_small.png             ← la misma mascota a 520×520 para que la web cargue rápido
├── data/
│   ├── documents/                 ← los 3 documentos del RAG
│   │   ├── aesan_recomendaciones_dieteticas_2022.pdf
│   │   ├── recetario_milo.md
│   │   └── tecnicas_y_sustituciones.md
│   ├── foods.csv                  ← 121 alimentos USDA con valores por 100 g
│   ├── recipes.json               ← 36 recetas con ingredientes en gramos
│   ├── sources.json               ← procedencia, versión y huella de cada fuente
│   └── usda/                      ← selección de alimentos y descargas oficiales de USDA
├── src/milo/                      ← el código de MILO
│   ├── __init__.py
│   ├── config.py                  ← rutas y lectura de .env
│   ├── models.py                  ← "moldes" de datos validados
│   ├── nutrition.py               ← catálogo de alimentos y calculadora
│   ├── recipes.py                 ← herramientas de cocina (recetas, menú, compra, perfil)
│   ├── rag.py                     ← todo el RAG
│   ├── agent.py                   ← grafo LangGraph, herramientas y memoria
│   ├── usda.py                    ← importador de los archivos oficiales de USDA
│   └── prompts/system.md          ← el system prompt
├── scripts/                       ← utilidades que se ejecutan desde la terminal
├── tests/                         ← pruebas automáticas
├── presentacion/                  ← diapositivas y guion de la defensa
└── storage/                       ← generado automáticamente: ChromaDB y memoria
```

| Carpeta | Para qué sirve |
|---|---|
| `data/` | Toda la información: documentos para el RAG, alimentos, recetas y procedencia |
| `src/milo/` | El "cerebro" del proyecto: el código que usan el notebook, la terminal y la web |
| `scripts/` | Programas pequeños para preparar datos, construir el índice o conversar por terminal |
| `tests/` | Pruebas que comprueban que todo funciona |
| `storage/` | Lo que el programa genera: el índice vectorial y la memoria de las conversaciones |
| `assets/` | Imágenes (la mascota) |
| `presentacion/` | Material para la defensa oral |

La idea importante: **solo hay una implementación de MILO**, la de `src/milo/`. El notebook, `scripts/chat.py` y
`app.py` la importan; ninguno duplica la lógica.

---

## 3. Los datos: carpeta `data/`

### 3.1. Qué datos hay y para qué se usan

| Archivo | Formato | Origen | ¿Original o generado? | Se usa para |
|---|---|---|---|---|
| `documents/aesan_recomendaciones_dieteticas_2022.pdf` | PDF | AESAN, Ministerio de Consumo (2022) | **Original** descargado | RAG |
| `documents/recetario_milo.md` | Markdown | Generado desde `recipes.json` | **Generado** por `prepare_recipes.py` | RAG |
| `documents/tecnicas_y_sustituciones.md` | Markdown | Redactado para el proyecto con referencias a FoodSafety.gov, USDA, NIDDK y NICHD | **Propio** | RAG |
| `foods.csv` | CSV | USDA FoodData Central | **Generado** por `build_catalog.py` desde los ZIP oficiales | Cálculos nutricionales |
| `recipes.json` | JSON | Recetas propias del proyecto | **Propio** (editado a mano y validado por script) | Herramientas de recetas, menú y compra |
| `sources.json` | JSON | Registro de fuentes | Propio (los hashes los actualizan los scripts) | Comprobar procedencia |
| `usda/*.zip` | ZIP con CSV o JSON | USDA FoodData Central | **Originales** descargados (no se suben a GitHub) | Construir `foods.csv` |
| `usda/seleccion_*.json` | JSON | Propio | Propio | Qué alimentos importar y su nombre en español |
| `usda/Download_Field_Descriptions_Oct2020.pdf` | PDF | USDA | Original | Diccionario de campos de USDA (consulta) |

### 3.2. Por qué tres formatos distintos

**PDF.** Utilizo el PDF de AESAN como fuente de conocimiento para el RAG. Es el documento oficial tal cual se publica.
El programa extrae su texto página a página, lo limpia, lo divide en fragmentos y los guarda en ChromaDB.

**Markdown (`.md`).** Mis dos documentos propios son texto con títulos (`## ...`). Es fácil de leer y de dividir por
secciones, y el RAG lo trata igual que el texto del PDF.

**CSV.** Utilizo CSV para la tabla de alimentos porque cada fila es un alimento y las columnas son sus valores: kcal,
proteína, hidratos, grasa y fibra por 100 g, estado (crudo, seco, cocinado…), alérgenos y si es vegano o vegetariano.
Es una tabla: el formato natural es una hoja de cálculo.

**JSON.** Utilizo JSON para las recetas porque una receta tiene estructura anidada: varios ingredientes (cada uno con
nombre, alimento, gramos y estado), varios pasos, etiquetas… Todo eso cabe ordenado en un solo registro. También uso
JSON para `sources.json` y para las selecciones de USDA.

### 3.3. Qué datos van al RAG y cuáles a los cálculos

- **RAG** (conocimiento en texto): solo los tres archivos de `data/documents/`. Son los que tienen
  `"usage": "rag_general"` en `sources.json`.
- **Cálculos nutricionales**: `foods.csv`. Nunca se envía entero a Gemini; lo usa Python.
- **Recetas, menús y lista de la compra**: `recipes.json` + `foods.csv`.

El recetario está en los dos lados a propósito: en `recipes.json` para que Python calcule, y en `recetario_milo.md`
para que el RAG pueda encontrar recetas por significado ("algo vegetariano con garbanzos").

### 3.4. El catálogo de alimentos (`foods.csv`)

Tiene **121 alimentos** (antes eran 70):

- 81 de **Foundation Foods** (abril 2026) y 4 de la edición JSON de octubre 2026: la base más moderna de USDA.
- 36 de **SR Legacy** (2018): la usé cuando Foundation no tenía el alimento o su registro no publicaba los cuatro
  macronutrientes (por ejemplo, la mantequilla, el puerro, la sandía y la sal).
- 119 tienen kcal, proteína, hidratos y grasa completos. Los 2 restantes (aceite de oliva virgen extra y aceite de
  girasol de Foundation) no publican esos valores; ninguna receta los usa, y el código nunca los convierte en cero.
- Cubre proteínas (pollo, pavo, ternera, cerdo, salmón, bacalao, pescadilla, sardinas, atún, gambas, mejillones,
  calamar, huevos, tofu), cereales (arroz, pasta, avena, pan, cuscús, quinoa, tortillas), lácteos (leches, yogures,
  queso fresco, mozzarella, requesón, parmesano, cheddar, cottage, mantequilla), unas 30 verduras y 18 frutas,
  legumbres (lentejas, garbanzos, alubias, guisantes), frutos secos y semillas, aceites y condimentos (sal, pimentón,
  orégano, vinagre, miel, cacao, chocolate negro, aceitunas).

Cada fila conserva el **FDC ID** original (`fdc_id`), la descripción exacta de USDA (`name_source`), la fuente y versión
(`source_id`, `source_version`) y los identificadores de los nutrientes usados (`nutrient_ids`, `nutrient_record_ids`).
Crudo y cocinado son registros distintos (`state`), y no hay FDC IDs repetidos.

Una limitación: **USDA no tiene merluza** como tal. He usado *Fish, whiting, mixed species, raw*, que incluye la
*Pacific whiting* (*Merluccius productus*, una merluza), y lo indico en el nombre ("Pescadilla o merluza") y en la nota.

### 3.5. Cómo se prepararon los datos

```text
USDA (ZIP oficiales) ──► data/usda/seleccion_*.json ──► scripts/build_catalog.py ──► data/foods.csv
                                                                                         │
data/recipes.json ──► scripts/prepare_recipes.py ──► valida con foods.csv ──► data/documents/recetario_milo.md
                                                                                         │
data/documents/* ──► scripts/build_index.py ──► fragmentos ──► Gemini Embeddings ──► storage/chroma
```

1. **Selección.** En `data/usda/seleccion_*.json` cada alimento tiene su FDC ID, la descripción exacta que espera
   encontrar en USDA, el nombre en español, el estado, los alérgenos y si es vegano o vegetariano.
2. **Importación.** `build_catalog.py` abre los ZIP, busca cada FDC ID, comprueba que la descripción coincide (si
   USDA la hubiera cambiado, se para), comprueba las unidades (g o kcal) y copia los valores por 100 g.
   Para la energía usa, por este orden, los nutrientes 2048, 2047 y 1008 de USDA.
3. **Limpieza de documentos.** Al leer el PDF se unen palabras partidas con guion, se arregla la ligadura "ﬁ"
   ("refi nadas" → "refinadas") y se omiten portada, índice y contraportada (páginas 1, 2 y 19).
4. **Recetas.** `prepare_recipes.py` comprueba cada receta (alimentos existentes, estados coherentes, nutrientes
   completos, alérgenos), marca su estado y genera el documento del recetario.
5. **Índice.** `build_index.py` crea los vectores y los guarda en ChromaDB.

### 3.6. Cómo añadir información

Está explicado en el [capítulo 16](#16-cómo-modificar-el-proyecto): añadir alimentos, recetas o documentos.

---

## 4. Los scripts: carpeta `scripts/`

Todos se ejecutan desde la carpeta del proyecto con el entorno `.venv` activado.

| Script | Para qué sirve | Lee | Genera o modifica | ¿Cada vez? | Comando |
|---|---|---|---|---|---|
| `build_index.py` | Prepara la base de conocimiento: lee los documentos, los divide en fragmentos, genera embeddings con Gemini y los guarda en ChromaDB | `data/documents/`, `data/sources.json` | `storage/chroma/` | No: solo al añadir o cambiar documentos (o la primera vez) | `python scripts/build_index.py` (`--rebuild` borra y crea de cero; `--dry-run` solo cuenta fragmentos, sin Gemini) |
| `chat.py` | Conversar con MILO en la terminal | Todo `src/milo/` | `storage/memoria.sqlite` | Cuando quiera usarlo | `python scripts/chat.py` · `--rag` solo RAG · `--hilo nombre` retoma una conversación · `--borrar nombre` borra una conversación |
| `prepare_recipes.py` | Valida las recetas y regenera el documento del recetario | `data/recipes.json`, `data/foods.csv` | `data/recipes.json` (estado y alérgenos), `data/documents/recetario_milo.md`, hashes en `data/sources.json` | Solo al añadir o editar recetas, o al editar `tecnicas_y_sustituciones.md` | `python scripts/prepare_recipes.py` |
| `build_catalog.py` | Regenera la tabla de alimentos desde los archivos oficiales de USDA | `data/usda/*.zip`, `data/usda/seleccion_*.json` | `data/foods.csv` | Solo al añadir alimentos | `python scripts/build_catalog.py` |
| `download_sources.py` | Descarga los PDF y ZIP registrados que falten y verifica su huella | `data/sources.json` | Archivos en `data/` y `data/sources.json` | Solo si faltan los ZIP de USDA (por ejemplo tras clonar el repositorio) | `python scripts/download_sources.py` |
| `run_notebook.py` | Ejecuta el notebook entero de principio a fin y guarda las salidas | `MILO_Proyecto_Final.ipynb` | El notebook y un kernel temporal en `storage/jupyter/` | Cuando quiera regenerar todas las salidas | `python scripts/run_notebook.py` |

Para usar MILO un día normal **no hay que ejecutar ningún script de preparación**: los datos y el índice ya están hechos.
Además, si falta el índice, MILO lo crea solo al arrancar.

---

## 5. El código: carpeta `src/milo/`

```text
              config.py  (rutas y .env)        models.py  (moldes de datos)
                    │                                 │
          ┌─────────┴─────────┐             ┌─────────┴─────────┐
       rag.py            nutrition.py  ◄──── recipes.py          usda.py
     (RAG + Gemini)    (catálogo y cálculos)  (herramientas de     (solo para
          │                                   cocina)              build_catalog.py)
          └────────────────► agent.py ◄────────────┘
                     (grafo LangGraph + memoria)
                                 │
            notebook · scripts/chat.py · app.py
```

| Módulo | Qué hace | Quién lo usa |
|---|---|---|
| `config.py` | Guarda las rutas del proyecto (`data/foods.csv`, `data/recipes.json`, el system prompt…) y lee la configuración del archivo `.env`: la clave de Gemini, los modelos y la carpeta `storage/`. | Todos |
| `models.py` | Define los "moldes" de datos con Pydantic: `Food` (alimento), `RecipeIngredient`, `Recipe`, `UserProfile` (perfil), `DietaryRestriction`, `NutritionResult`, `DataSource`, `DocumentChunk` (fragmento). Si llega un dato imposible (un peso negativo, una unidad que no es gramos, un alérgeno desconocido), se rechaza en vez de aceptarlo en silencio. | Todos |
| `nutrition.py` | Contiene el **catálogo** de alimentos (`FoodCatalog`: buscar por nombre aunque falten tildes o esté en plural, y resolver ambigüedades) y la **calculadora**: `calculate_nutrition` suma valor por 100 g × gramos / 100 de cada ingrediente. También comprueba restricciones (`validate_recipe`) y escala recetas (`adjust_portions`, `scale_recipe`). Así Gemini nunca tiene que inventar cantidades. | `recipes.py`, scripts, tests |
| `recipes.py` | La clase `Kitchen` con toda la lógica de cocina: buscar recetas (y modo nevera), ver o escalar una receta, sustituir ingredientes, calcular un plato libre, crear un menú semanal y la lista de la compra. También `update_profile` y `describe_profile` para el perfil. Todo es Python determinista: no llama a Gemini. | `agent.py` (herramientas) y `app.py` (Mi nevera y Plan semanal) |
| `rag.py` | Todo el RAG: leer documentos, limpiar, dividir en fragmentos, crear embeddings, guardar y consultar ChromaDB, y generar respuestas con Gemini. La clase principal es `NutritionRAG`. También crea el modelo de Gemini con reintentos y respaldo (`create_model`) y carga el system prompt. | `agent.py`, notebook, `scripts/` |
| `agent.py` | El agente: define el estado, las 8 herramientas (`make_tools`), el grafo de LangGraph (`MiloAgent`) y la memoria SQLite. Su método `ask(pregunta, thread_id=...)` es la puerta de entrada para el notebook, la terminal y la web. | Notebook, `scripts/chat.py`, `app.py` |
| `usda.py` | Lee las tablas oficiales de USDA dentro de los ZIP y crea objetos `Food`. | Solo `scripts/build_catalog.py` y sus tests |
| `prompts/system.md` | El system prompt (capítulo 6). | `rag.py` lo carga |

No hay módulos separados de "herramientas" ni de "memoria": las herramientas están en `make_tools()` dentro de
`agent.py` (y su lógica en `recipes.py`), y la memoria es el checkpointer que crea `MiloAgent._memory()` en `agent.py`.

---

## 6. El system prompt y los demás prompts

### Dónde está

**`src/milo/prompts/system.md`**. Es un archivo de texto normal: se puede abrir en VS Code y leer o editar.

### Qué es un system prompt

Son las instrucciones "de fondo" que recibe el modelo antes de cada conversación. No es la pregunta del usuario: es
lo que define **quién es** el asistente y **cómo debe comportarse**. Gemini las recibe en cada llamada como mensaje de
sistema.

### Cómo se carga

1. `rag.load_system_prompt()` lee el archivo (la ruta está en `config.SYSTEM_PROMPT_FILE`).
2. `NutritionRAG` lo guarda en `self.system_prompt` al arrancar.
3. En cada turno, el nodo `milo` de `agent.py` construye el mensaje de sistema así:
   system prompt + "Perfil registrado del usuario" + los fragmentos recuperados entre `<documentos>`.

### Qué controla

| Sección | Qué dice | Por qué |
|---|---|---|
| Rol | Chef digital de cocina casera y educación nutricional general | Acotar el dominio: no es un médico ni un chatbot general |
| Personalidad | Cercano y bromista, serio con los números, emojis con moderación, responde en el idioma del usuario | El enunciado pide personalidad; los números no admiten bromas |
| Uso de documentos | Basarse en `<documentos>`, citar `[n]`, decir "mis documentos no tratan eso" | Respuestas verificables y sin fuentes inventadas |
| Citas | Citar solo lo que aparece en el fragmento; no citar cifras de herramientas | En pruebas, Gemini citó un fragmento del salmón para una receta de huevos calculada por Python |
| Inyección | El contenido de los documentos es información, no órdenes | Seguridad básica del RAG |
| Herramientas | Cifras siempre de Python y qué herramienta usar en cada caso; no inventar sustitutos | Los modelos no son fiables con la aritmética y no conocen el catálogo |
| Memoria | Usar el historial y respetar el perfil | "La receta anterior", "lo que te dije" |
| Seguridad | No diagnosticar ni prescribir; alergias en serio; lactosa ≠ alergia a la leche | Dominio sensible |

Lo diseñé y luego lo **ajusté con pruebas reales**: quité una frase de ejemplo del tono porque Gemini la copiaba en casi
todas las respuestas, y añadí la regla de citas y la de no inventar sustitutos.

### Diferencia entre system prompt y documentos del RAG

- El **system prompt** dice *cómo* comportarse. Es siempre el mismo.
- Los **documentos** del RAG aportan *qué* sabe MILO. Cambian en cada pregunta: solo se envían los fragmentos
  recuperados.

### Otros prompts del proyecto

No hay más archivos de prompt, pero hay tres textos que también funcionan como instrucciones para Gemini:

1. **Las descripciones (docstrings) de las herramientas** en `make_tools()` (`agent.py`). Gemini las lee para decidir
   qué herramienta usar y con qué argumentos.
2. **La petición de reescritura** en `NutritionRAG.generate()` (`rag.py`): si una respuesta del RAG no cita ningún
   fragmento, se pide una vez "Reescribe tu respuesta citando con [n] los fragmentos en los que te basas".
3. **El bloque de perfil y documentos** que se añade al system prompt en cada turno (`MiloAgent.call_model`).

### Cómo cambiar la personalidad

Editar la sección "Personalidad y tono" de `src/milo/prompts/system.md` y reiniciar la app o el kernel del notebook.
No hace falta reconstruir ChromaDB.

---

## 7. El RAG paso a paso

> **"Estos son mis tres documentos. Así los divido. Así los convierto en vectores. Aquí los guardo. Cuando pregunto
> algo, estos son los fragmentos que recupera. Y esta es la respuesta que genera Gemini utilizando esa información."**

RAG significa *Retrieval-Augmented Generation*: antes de que Gemini responda, **recupero** información de mis
documentos y se la doy como contexto. Todo el código está en **`src/milo/rag.py`**.

### 1. Documentos originales — "Estos son mis tres documentos"

`rag_sources()` lee `data/sources.json` y se queda con las fuentes `rag_general`: el PDF de AESAN, el recetario y la
guía de técnicas. `check_source()` calcula la huella SHA-256 de cada archivo y la compara con la registrada: si alguien
cambia un documento sin registrarlo, la ingesta se detiene. Así sé que el índice corresponde a los documentos actuales.

### 2. Extracción

`load_documents()` lee el PDF página a página con la librería `pypdf` (`ingest_pdf`) y los Markdown completos.

### 3. Limpieza

`clean_text()` quita caracteres de control, une palabras cortadas con guion al final de línea, arregla la ligadura "ﬁ"
del PDF y normaliza espacios. Del PDF omito las páginas 1, 2 y 19 (portada, índice y contraportada; están en
`skip_pages` de `sources.json`). En una primera versión el índice del PDF salía como primer resultado de casi todas las
búsquedas, porque menciona todos los temas.

### 4. Chunking — "Así los divido"

- `split_sections()` separa por títulos: líneas que empiezan por `## ` (Markdown) o líneas en MAYÚSCULAS (PDF).
- `chunk_page()` corta cada sección en fragmentos de **hasta 400 palabras**, con **50 palabras de solapamiento** si
  una sección es más larga, para no perder una frase en el corte.
- En el PDF uno las secciones muy cortas con la siguiente para no crear fragmentos de dos palabras.

Resultado actual: **83 fragmentos** = 35 de AESAN + 37 del recetario (uno por cada una de las 36 recetas y otro para la
introducción) + 11 de técnicas, en total unas 9.900 palabras. Como cada receta es un fragmento propio, "receta con
garbanzos" encuentra exactamente las recetas con garbanzos.

### 5. Gemini Embeddings — "Así los convierto en vectores"

`create_embeddings()` usa el modelo **`gemini-embedding-001`**, que convierte cada fragmento en una lista de **3072
números**. Esa lista representa el *significado* del texto: dos textos que hablan de lo mismo tienen vectores
parecidos aunque usen palabras distintas. "3072 dimensiones" significa simplemente que cada vector tiene 3072 números.

### 6. ChromaDB — "Aquí los guardo"

`index_chunks()` guarda en ChromaDB, carpeta **`storage/chroma/`**, cada fragmento con:

- su **identificador** (huella del contenido, estable entre ejecuciones),
- su **texto**,
- su **vector**,
- sus **metadatos**. Ejemplo real:

```text
{'source_id': 'AESAN_2022', 'page': 9, 'section': 'Contenido', 'version': '2022-12', 'usage': 'rag_general',
 'source_url': 'https://www.aesan.gob.es/.../RECOMENDACIONES_DIETETICAS.pdf', 'source_sha256': '8a7027de…'}
```

Los fragmentos Markdown no tienen `page`, pero sí `section` (por ejemplo `r023 — Ensalada de pollo y aguacate`).

La colección se llama `milo_` + una huella del modelo y de los fragmentos (ahora `milo_51435337a2aab599`). Si cambio un
documento, cambia el nombre y se crea una colección nueva: nunca se mezclan vectores antiguos. Solo se generan los
embeddings que faltan, así que reindexar no duplica nada.

**Cuándo se construye el índice:** con `python scripts/build_index.py`, o automáticamente la primera vez que se crea
`NutritionRAG` si falta (por ejemplo en Streamlit Cloud). **Cómo se reconstruye:** `python scripts/build_index.py --rebuild`.

### 7 y 8. Búsqueda y recuperación — "Estos son los fragmentos que recupera"

`NutritionRAG.retrieve(pregunta, k=4)`:

1. Convierte la pregunta en un vector con el mismo modelo de embeddings.
2. Pide a Chroma los **4 fragmentos más cercanos** según la **distancia coseno** (0 = mismo significado; cuanto
   menor, más parecido).
3. Devuelve cada fragmento numerado (`citation` 1, 2, 3, 4) con su texto, metadatos y distancia.

Ejemplo real: "¿Cuántos huevos puedo comer a la semana?" → primer fragmento `AESAN_2022 — página 9` ("máximo de 4
huevos medianos a la semana") con distancia 0,22; después la página 18 (0,32) y la 10 (0,32).

### 9. Generación — "Y esta es la respuesta que genera Gemini"

`NutritionRAG.generate()` (y, en el agente, el nodo `milo`) envía a Gemini:

```text
[sistema]  contenido de system.md
[usuario]  <documentos>
           [1] AESAN_2022 — página 9
           9 HUEVOS CON MODERACIÓN… máximo de 4 huevos medianos a la semana…
           [2] AESAN_2022 — página 18
           …
           </documentos>
           Pregunta: ¿Cuántos huevos puedo comer a la semana?
```

Gemini responde apoyándose en esos fragmentos y escribe `[1]`, `[2]` donde se basa en ellos. `cited_numbers()` detecta
qué números ha citado: en el notebook aparecen marcados con ★ y en la app se resaltan en naranja en el desplegable
"Fragmentos recuperados de ChromaDB". Si una respuesta del RAG no cita nada, se le pide una vez que la reescriba citando.

---

## 8. LangGraph: el agente

### Qué es LangGraph y por qué lo uso

LangGraph es una librería para construir agentes como **grafos**: cada paso es un **nodo** (una función de Python) y las
flechas (**aristas**) dicen qué paso va después. Entre pasos viaja un **estado** con la conversación. Lo uso porque hace
visible el flujo del agente, permite que el agente repita pasos (usar varias herramientas seguidas) y trae la memoria
(checkpointers) incorporada.

### Dónde está

`src/milo/agent.py`, clase `MiloAgent`. El grafo se construye en su `__init__`.

### El grafo real

```text
START ──► recuperar ──► milo ──¿Gemini pide una herramienta?──► sí ──► herramientas ──┐
                         ▲                                                            │
                         └────────────────────────────────────────────────────────────┘
                         └──► no ──► END
```

```python
graph.add_edge(START, "recuperar")
graph.add_edge("recuperar", "milo")
graph.add_conditional_edges("milo", tools_condition, {"tools": "herramientas", END: END})
graph.add_edge("herramientas", "milo")
```

- **Estado** (`MiloState`): `messages` (historial), `profile` (perfil del usuario) y `fragments` (fragmentos del turno).
- **Nodo `recuperar`** (`MiloAgent.retrieve`): busca en ChromaDB 4 fragmentos con la última pregunta. Si la pregunta
  tiene menos de 6 palabras ("¿y cuántas calorías tiene?"), le añade la pregunta anterior para que la búsqueda tenga
  sentido. Así **cada consulta usa la base de conocimiento**.
- **Nodo `milo`** (`MiloAgent.call_model`): envía a Gemini el system prompt, el perfil, los fragmentos y los últimos 8
  turnos. Gemini tiene las herramientas "atadas" (`bind_tools`): puede responder con texto o con una **petición de
  herramienta** (nombre + argumentos).
- **Arista condicional** (`tools_condition`, de LangGraph): si el último mensaje de Gemini pide una herramienta, va a
  `herramientas`; si no, termina.
- **Nodo `herramientas`** (`ToolNode`, de LangGraph): ejecuta la herramienta en Python y añade el resultado al historial
  como mensaje de herramienta. Si la herramienta falla (por ejemplo, un alimento que no existe), el error se devuelve a
  Gemini para que lo corrija. Después vuelve a `milo`.

### Qué pasa cuando envío un mensaje

Ejemplo real: *"Tengo pollo, arroz, aguacate y huevos. Quiero una cena de unas 800 kcal y bastante proteína."*

1. `ask()` añade el mensaje al estado del `thread_id` de la conversación.
2. `recuperar` trae del recetario el bowl de pollo y arroz, la ensalada de pollo y aguacate, las tostadas…
3. `milo`: Gemini decide llamar a `buscar_recetas(ingredientes=[...])`.
4. `herramientas`: Python devuelve las recetas compatibles, qué tengo y qué me falta.
5. `milo`: Gemini decide llamar a `ver_receta(recipe_id="r001", objetivo_kcal=800)`.
6. `herramientas`: Python escala el bowl a 800 kcal y calcula 58 g de proteína.
7. `milo`: Gemini ya no necesita nada más y redacta la respuesta con esas cifras → END.
8. LangGraph guarda el estado en la memoria; la app pinta la respuesta y la ficha calculada.

Hay un límite de seguridad de 16 pasos por turno (`recursion_limit`) para que el agente nunca entre en un bucle infinito.

---

## 9. Las herramientas del agente

Hay **8 herramientas**, definidas en `make_tools()` (`agent.py`). Todas llaman a Python; ninguna inventa datos.

| Herramienta | Qué hace | Cuándo la usa MILO | Qué consulta | Qué devuelve |
|---|---|---|---|---|
| `buscar_recetas` | Busca recetas compatibles con el perfil, con filtros (tipo de comida, kcal máximas, proteína mínima, tiempo, texto) y modo nevera | "Recomiéndame…", "¿qué hago con lo que tengo?" | `recipes.json`, `foods.csv`, perfil | Lista de recetas con kcal, proteína, tiempo, dieta y, con ingredientes, qué tienes y qué te falta |
| `ver_receta` | Ficha completa de una receta; cambia raciones o la escala a unas kcal (entre ×0,5 y ×2) | "Dame la receta", "¿cuántas calorías tiene?", "para 2 personas", "a 700 kcal" | `recipes.json`, `foods.csv` | Ingredientes en gramos, pasos, macros por ración y totales, alérgenos y avisos |
| `sustituir_ingrediente` | Cambia un ingrediente por otro del catálogo y recalcula. Por defecto usa la cantidad con energía parecida (nunca gramo a gramo). Sin sustituto, propone 4 alternativas del catálogo con un reparto de energía parecido | "No tengo X", "cámbialo por Y" | `recipes.json`, `foods.csv`, perfil | Cambio realizado y macros antes/después, o una lista de alternativas ya calculadas |
| `calcular_plato` | Calcula macros de un plato libre con alimentos y gramos | Propuestas fuera del recetario o ajustar cantidades a un objetivo | `foods.csv` | Ficha con macros; si un alimento no existe o es ambiguo, un error con opciones |
| `plan_semanal` | Menú de 1–7 días con 3 o 4 comidas, escalando recetas hacia las kcal diarias | "Hazme un menú…" | `recipes.json`, `foods.csv`, perfil | Comidas por día con cantidades y totales; a Gemini le llega un resumen y a la app el detalle |
| `lista_compra` | Suma los ingredientes del último menú (o de unas recetas) y los agrupa por categorías | "La lista de la compra de ese menú" | El último menú guardado en la memoria | Productos con gramos por categoría |
| `guardar_perfil` | Guarda dieta, alergias, intolerancias, alimentos que no gustan, objetivo, kcal o preferencias | "Soy vegetariano", "soy alérgico a…" | `foods.csv` (para reconocer alimentos) | Perfil actualizado en el estado de LangGraph |
| `buscar_documentos` | Búsqueda adicional en ChromaDB con otra consulta | Cuando los fragmentos del turno no bastan | ChromaDB | Fragmentos nuevos numerados a continuación de los anteriores |

Dos detalles importantes:

- El **perfil** y el **historial** no los rellena Gemini: LangGraph los inyecta en las herramientas (`InjectedState`).
  Por eso Gemini no puede "saltarse" una restricción: `validate_recipe` en Python descarta las recetas incompatibles.
- Si el usuario tiene **alergias registradas**, MILO tampoco recomienda productos comerciales (pan, pasta, conservas,
  tofu, hummus, crema de cacahuete…), porque sus alérgenos dependen de la marca. Sin alergias, solo avisa de revisar la
  etiqueta.

---

## 10. La memoria

### Qué es

La memoria es lo que permite que MILO recuerde lo que hemos hablado. Sin ella, cada mensaje sería una conversación nueva.

### Dónde se guarda y qué es SQLite

En **`storage/memoria.sqlite`**. SQLite es una base de datos que vive en **un solo archivo**: no necesita instalar ni
arrancar ningún servidor. La uso porque es sencilla, viene con Python y permite que la memoria sobreviva a cerrar el
programa. Los archivos `memoria.sqlite-shm` y `memoria.sqlite-wal` son auxiliares de SQLite y forman parte de ella.

### Qué contiene

Por cada conversación: todos los mensajes (míos, de Gemini y los resultados de las herramientas), el perfil y los
fragmentos del último turno. Por eso la herramienta `lista_compra` puede encontrar "ese menú" en el historial.

### Cómo se relaciona con LangGraph

LangGraph tiene **checkpointers**: componentes que guardan el estado del grafo después de cada paso. Uso `SqliteSaver`
(en `MiloAgent._memory()`). Al compilar el grafo le paso ese checkpointer, y LangGraph se encarga del resto.

### Qué ocurre entre mensajes y al reiniciar

- Entre mensajes: `ask()` recupera el estado guardado del `thread_id`, añade el nuevo mensaje y lo vuelve a guardar.
- A Gemini le envío los **últimos 8 turnos** para no gastar tokens; el historial completo sigue guardado.
- Al reiniciar el programa: como está en un archivo, la conversación sigue ahí. En el notebook lo demuestro creando un
  agente nuevo que recuerda que "soy vegetariano".

### Cómo se separan las conversaciones

Cada conversación tiene un **`thread_id`** distinto. En la app, el identificador va en la dirección
(`http://localhost:8501/?c=...`): si recargo la página sigue la misma charla; el botón "Nueva conversación" crea otro.
En la terminal se elige con `--hilo`.

### Cómo borrar una conversación sin tocar las demás

```powershell
python scripts/chat.py --borrar NOMBRE_DEL_HILO
```

Usa `delete_thread()` de LangGraph y solo borra ese hilo (en la app, el nombre del hilo es lo que aparece después de
`?c=` en la dirección). **No conviene borrar `storage/memoria.sqlite` entero** salvo que quiera olvidar todas las
conversaciones, incluidas las del notebook.

---

## 11. La API de Gemini

### Qué es una API

Una **API** es una forma de que un programa use un servicio de otro. Gemini funciona en los servidores de Google: mi
programa le envía un mensaje por Internet y recibe la respuesta. **La API no es la aplicación**: MILO (Python,
LangGraph, ChromaDB, Streamlit) se ejecuta en mi ordenador; solo "pregunta" a Gemini cuando necesita un modelo de
lenguaje o embeddings.

| Quién | Qué hace |
|---|---|
| **Streamlit** (`app.py`) | Dibuja la web, recoge mis mensajes y muestra las respuestas. No sabe nada de IA |
| **LangGraph** (`agent.py`) | Organiza los pasos del agente y la memoria |
| **ChromaDB** | Guarda y busca vectores, en mi ordenador |
| **Python** (`nutrition.py`, `recipes.py`) | Hace todos los cálculos |
| **Gemini** (en Google) | Convierte textos en vectores y redacta respuestas o decide herramientas |

### La API key

La **API key** es una contraseña personal que identifica mis llamadas a Gemini. Se guarda en el archivo **`.env`** de la
raíz (`GOOGLE_API_KEY=...`), que nunca se sube a GitHub. `config.Settings` (con la librería pydantic-settings) la lee
automáticamente. En Streamlit Cloud se guarda en *Secrets* y `app.py` la pasa a una variable de entorno.

### Qué partes se conectan a Gemini

| Momento | Modelo | Código |
|---|---|---|
| Crear el índice (embeddings de los 83 fragmentos) | `gemini-embedding-001` | `rag.index_chunks` |
| Cada pregunta (embedding de la pregunta para buscar en Chroma) | `gemini-embedding-001` | `NutritionRAG.retrieve` |
| Cada paso del nodo `milo` (decidir herramienta o redactar) | `gemini-3.5-flash-lite` | `MiloAgent.call_model` |
| Respuesta del RAG sin agente (notebook, `chat.py --rag`) | `gemini-3.5-flash-lite` | `NutritionRAG.generate` |

Los cálculos, Mi nevera y el Plan semanal **no** usan Gemini.

### Qué pasa si no hay conexión o Gemini falla

- **Error 503 (UNAVAILABLE):** el modelo está saturado en ese momento. Es un problema temporal de Google, no del código.
- **Error 429:** he superado el límite de llamadas por minuto.
- `create_model()` configura **3 reintentos** automáticos, un **límite de 15 llamadas por minuto** (para no superar la
  cuota gratuita) y un **modelo de respaldo** (`gemini-3.1-flash-lite`): si el principal falla, LangChain repite la
  llamada con el de respaldo (`with_fallbacks`).
- Si aun así falla, la app muestra "Gemini está saturado en este momento…" y el resto de secciones siguen funcionando.
- Sin Internet: el chat no puede responder, pero Mi nevera, Plan semanal y Mi perfil funcionan igual.

---

## 12. La web con Streamlit

### Qué es Streamlit

Una librería para crear páginas web escribiendo solo Python. Cada vez que hago algo en la página (pulsar un botón,
escribir un mensaje), Streamlit vuelve a ejecutar `app.py` de arriba abajo y redibuja la pantalla.

### Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Archivo que inicia la web | `app.py` (`streamlit run app.py`) |
| Colores del tema | `.streamlit/config.toml` (`primaryColor`, `backgroundColor`…) y constantes `ORANGE`, `CREAM`, `GREEN`, `CHARCOAL` al principio de `app.py` |
| Tipografías | `.streamlit/config.toml`: `font` (DM Sans, texto) y `headingFont` (Nunito, títulos), de Google Fonts (licencia SIL OFL, sin archivos de fuente en el proyecto); tamaño base 17 px en `baseFontSize` |
| CSS adicional | Constantes `CSS` (tarjetas, chips, cabeceras, ajustes para móvil) y `CHAT_CSS` (columna del chat de 820 px) en `app.py` |
| Iconos | Material Symbols Rounded (`:material/nombre:`), que ya vienen con Streamlit, en botones, menú y desplegables; y unos pocos iconos SVG de Lucide (licencia ISC) en el diccionario `ICONS` para las tarjetas. Sin librerías extra |
| Mascota | `assets/milo_small.png` (constante `MASCOT`), PNG transparente sin recuadros |

### Cómo se construyen las pantallas

- La **barra lateral** muestra la mascota, el logotipo, el menú de secciones (`st.radio` con `key="page"`), un resumen
  del perfil y el botón "Nueva conversación".
- Cada sección es una función: `page_chat`, `page_fridge`, `page_plan` y `page_profile`. Al final de `app.py`,
  `PAGES[state.page][1]()` ejecuta la de la sección elegida.
- Las tarjetas (`recipe_card`, `plan_view`, `shopping_view`, `search_view`) muestran los resultados de las herramientas.

### Cómo funciona el chat y cómo se comunica con el backend

1. `st.chat_input` recibe el mensaje.
2. `ask_milo()` llama a `agent.ask(pregunta, thread_id=state.thread_id, profile=state.profile)`. El agente se crea una
   sola vez (`@st.cache_resource`) y se comparte.
3. La respuesta trae el texto de Gemini, los resultados de las herramientas y los fragmentos del RAG.
4. Se dibuja con `st.chat_message`: el texto, las tarjetas calculadas por Python y el desplegable con los fragmentos de
   ChromaDB (los citados, en naranja).
5. Si el perfil cambió (por ejemplo con `guardar_perfil`), la app lo sincroniza.

El chat ocupa una columna centrada de 820 px (y la caja de escritura está alineada con ella), como ChatGPT; en móvil
ocupa todo el ancho. Lo hago con `CHAT_CSS`, que solo se aplica en la sección Chat y usa los identificadores
`data-testid` de Streamlit, que son estables.

### Cómo se mantiene la conversación

- `st.session_state` guarda el `thread_id`, el perfil, los mensajes mostrados y el último menú mientras la pestaña está
  abierta.
- La memoria real está en LangGraph (`storage/memoria.sqlite`). Al recargar, `restore_turns()` reconstruye los mensajes
  a partir de ella.

### Qué hace cada sección

| Sección | Qué hace | ¿Usa Gemini? |
|---|---|---|
| **Chat** | Conversación con el agente completo, con sugerencias de inicio | Sí |
| **Mi nevera** | Elijo ingredientes y filtros; muestra recetas con lo que tengo y lo que falta; botón para pasar la idea al chat | No |
| **Plan semanal** | Elijo kcal, días y comidas; muestra el menú, un gráfico por día y la lista de la compra descargable | No |
| **Mi perfil** | Formulario de dieta, alergias, intolerancias, alimentos que no gustan, objetivo y kcal | No |

### Cómo cambiar el aspecto

- Colores y fuentes generales: `.streamlit/config.toml` (reiniciar Streamlit después).
- Tamaños, tarjetas y anchura del chat: constantes `CSS` y `CHAT_CSS` de `app.py`.
- Textos de bienvenida y sugerencias: `page_chat()` y la lista `SUGGESTIONS`.

---

## 13. Las pruebas: carpeta `tests/`

### Qué son

Programas que comprueban automáticamente que el código hace lo que debe. Por ejemplo: "si 100 g de un alimento tienen
100 kcal, 150 g deben dar 150 kcal". Si alguien cambia el código y rompe algo, una prueba falla y avisa.

### Qué se prueba

| Archivo | Nº | Qué comprueba |
|---|---|---|
| `test_nutrition.py` | 33 | La calculadora: sumas, raciones, datos ausentes (nunca cero), crudo ≠ cocinado, cantidades y unidades inválidas |
| `test_constraints.py` | 18 | Restricciones (alergias, dietas, alimentos que no gustan), búsqueda de alimentos por nombre y escalado de recetas |
| `test_data_pipeline.py` | 9 | Que los 121 alimentos coinciden con los archivos oficiales de USDA, las huellas de las fuentes y que las recetas son coherentes |
| `test_usda_import.py` | 6 | El importador de USDA con archivos de prueba: unidades, duplicados, energía |
| `test_ingestion.py` | 5 | La limpieza y el chunking, y la lectura real del PDF de AESAN |
| `test_rag.py` | 12 | Corpus, nombre de la colección, detección de citas, reescritura sin citas y **5 pruebas reales con Gemini** |
| `test_recipes.py` | 9 | Nevera, perfil, escalado, sustituciones, plato libre, menú semanal y lista de la compra con los datos reales |
| `test_agent.py` | 6 | El grafo con un Gemini **simulado** (herramientas, memoria, aislamiento, errores) y **1 prueba real** |

### Pruebas sin API y pruebas reales

- **Sin API (92):** usan datos reales del proyecto, pero no llaman a Gemini (o usan un Gemini simulado que devuelve
  respuestas preparadas). Son rápidas (unos 6 segundos) y gratuitas.
- **Reales (6, marcadas `live`):** llaman de verdad a Gemini y a ChromaDB. Comprueban que la búsqueda recupera el
  documento esperado, que Gemini cita y que la memoria funciona. Tardan alrededor de un minuto y gastan cuota.

### Cómo se ejecutan

```powershell
python -m pytest            # 92 pruebas sin API → "92 passed, 6 skipped"
python -m pytest --live     # las 98, incluidas las reales → "98 passed"
```

"Passed" significa que el resultado fue el esperado; "skipped", que esa prueba se omitió a propósito (las reales sin
`--live`). Una prueba real puede fallar sin que el código esté mal si Gemini está saturado o no hay conexión. Las que
comparan con USDA se omiten si no están los ZIP (por ejemplo, en un clon recién descargado de GitHub).

No hace falta ejecutarlas cada vez que abro MILO: solo después de cambiar código o datos.

---

## 14. La carpeta `storage/`

`storage/` contiene solo lo que el programa genera. No se sube a GitHub (`.gitignore`).

| Ruta | Qué es | ¿Necesario? | Si lo borro… |
|---|---|---|---|
| `storage/chroma/` | El índice vectorial: `chroma.sqlite3` (textos, metadatos y registro) y carpetas con los vectores | Sí, para el RAG | Se regenera con `python scripts/build_index.py` o solo al arrancar MILO (83 embeddings, unos segundos) |
| `storage/memoria.sqlite` (+ `-shm`, `-wal`) | La memoria de todas las conversaciones | Sí, para recordar | Se pierden **todas** las conversaciones guardadas; se crea vacío al volver a usar MILO |
| `storage/jupyter/` | Definición temporal del kernel que crea `run_notebook.py` | No | Se vuelve a crear la próxima vez que se ejecuta ese script |

Puedo borrar con seguridad `storage/jupyter/`. Para la memoria, mejor borrar conversaciones concretas con
`python scripts/chat.py --borrar HILO`. Antes de borrar `chroma/` o `memoria.sqlite` conviene cerrar la app y el
notebook.

---

## 15. Cómo ejecutar MILO desde cero

### Uso habitual (cualquier día): dos comandos

Abro la carpeta del proyecto en VS Code, abro una terminal (*Terminal → Nueva terminal*) y:

```powershell
.venv\Scripts\Activate.ps1
streamlit run app.py
```

Se abre <http://localhost:8501>. Para cerrar la app: **Ctrl + C** en la terminal.

### Primera instalación (solo una vez)

1. **Abrir Visual Studio Code** → *Archivo → Abrir carpeta…* → `milo_cooking_agent`.
2. **Abrir la terminal**: *Terminal → Nueva terminal* (es PowerShell).
3. **Crear el entorno virtual**:
   ```powershell
   python -m venv .venv
   ```
4. **Activarlo** (cada vez que abra una terminal nueva):
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
   Si PowerShell lo bloquea: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y repetir. Al activarse, la línea
   empieza por `(.venv)`.
5. **Instalar las dependencias**:
   ```powershell
   python -m pip install -r requirements.txt
   ```
6. **Configurar la API key**:
   ```powershell
   copy .env.example .env
   notepad .env
   ```
   Escribir la clave después de `GOOGLE_API_KEY=` y guardar. Para comprobar que se lee (sin mostrarla):
   ```powershell
   python -c "from milo.config import Settings; Settings().require_key(); print('Clave OK')"
   ```
7. **(Opcional) Construir el índice** — si no, se crea solo la primera vez:
   ```powershell
   python scripts/build_index.py
   ```
   Debe terminar con `Vectores guardados …: 83`.

### Cada forma de usar MILO

| Qué | Comando |
|---|---|
| App web | `streamlit run app.py` → abrir <http://localhost:8501> |
| Agente por terminal | `python scripts/chat.py` (escribir `salir` para terminar) |
| Solo RAG por terminal | `python scripts/chat.py --rag` |
| Notebook | Abrir `MILO_Proyecto_Final.ipynb`, elegir el kernel de `.venv` (arriba a la derecha) y pulsar *Run All*; o `python scripts/run_notebook.py` |
| Pruebas | `python -m pytest` (sin API) · `python -m pytest --live` (con Gemini) |
| Cerrar | `Ctrl + C` en la terminal donde se está ejecutando |

---

## 16. Cómo modificar el proyecto

**Añadir un alimento.** Los valores vienen de USDA para no inventar nada.
1. Buscar el alimento en <https://fdc.nal.usda.gov/> y anotar su FDC ID y su descripción exacta.
2. Añadir una entrada al archivo de selección que corresponda (`data/usda/seleccion_foundation_2026_04.json` o
   `seleccion_sr_legacy.json`) copiando una existente: `fdc_id`, `expected_description`, `name_es`, `state`,
   `allergens`, `vegan`, `vegetarian`, `is_compound`, `allergen_review_complete` y `notes`.
3. `python scripts/build_catalog.py` (si faltan los ZIP: `python scripts/download_sources.py` antes).
4. `python -m pytest` para comprobar que coincide con USDA.

**Añadir una receta.**
1. Añadir un objeto a `data/recipes.json` copiando uno existente: `recipe_id` nuevo (`r037`), `title`, `servings`,
   `ingredients` (cada uno con un `food_id` de `foods.csv`, `grams` y el mismo `state` que ese alimento), `steps`,
   `time_minutes_estimate`, `difficulty` (`fácil` o `media`) y `tags` (`desayuno`, `comida`, `cena`, `snack`).
2. `python scripts/prepare_recipes.py` — la valida y regenera `recetario_milo.md`. Si sale `pending`, imprime el motivo.
3. `python scripts/build_index.py` — indexa el recetario actualizado.

**Añadir otro documento PDF al RAG.**
1. Copiarlo a `data/documents/`.
2. Añadir una entrada en `data/sources.json` con `"usage": "rag_general"`, `"file_type": "pdf"`, `"status": "downloaded"`,
   `source_id`, `path`, `url`, `title`, `version`, `usage_conditions`, `size_bytes` y `sha256` (en PowerShell:
   `(Get-FileHash archivo.pdf -Algorithm SHA256).Hash.ToLower()`).
3. `python scripts/build_index.py`.

**Reconstruir ChromaDB.** `python scripts/build_index.py --rebuild`.

**Cambiar el system prompt o la personalidad.** Editar `src/milo/prompts/system.md` y reiniciar la app o el kernel.

**Cambiar la mascota.** Sustituir `assets/milo.png` y `assets/milo_small.png` (la app usa la pequeña; mejor PNG con
fondo transparente).

**Cambiar colores y tipografías.** `.streamlit/config.toml` (tema) y las constantes de color y `CSS` de `app.py`.

**Añadir una herramienta al agente.**
1. Programar la lógica como método de `Kitchen` en `src/milo/recipes.py`.
2. En `make_tools()` de `src/milo/agent.py`, crear una función con `@tool(response_format="content_and_artifact")`, una
   docstring clara (es lo que lee Gemini) y que devuelva `(texto_json, resultado)`. Añadirla a la lista final.
3. Mencionarla en "Cómo usar las herramientas" del system prompt.
4. Si debe verse en la app, añadir su tipo a `render_result()` de `app.py`.
5. Añadir una prueba en `tests/test_recipes.py`.

---

## 17. Problemas habituales

| Problema | Causa | Solución |
|---|---|---|
| `Falta GOOGLE_API_KEY` | No existe `.env` o la clave está vacía | `copy .env.example .env` y escribir la clave |
| "Gemini está saturado" / `503` | Demanda alta en Google | Esperar unos segundos y repetir (ya hay reintentos y modelo de respaldo) |
| `429` | Límite de la cuota gratuita | Esperar un minuto |
| `El documento X ha cambiado y no coincide con sources.json` | Se editó un documento sin registrar su huella | `python scripts/prepare_recipes.py` (documentos propios) y `python scripts/build_index.py` |
| ChromaDB vacío | Se borró `storage/` | `python scripts/build_index.py` (o arrancar MILO) |
| `ModuleNotFoundError` | Entorno no activado o dependencias sin instalar | Activar `.venv` y `python -m pip install -r requirements.txt` |
| `streamlit` no se reconoce | Entorno no activado | `.venv\Scripts\Activate.ps1` o `python -m streamlit run app.py` |
| Puerto ocupado | Otra app en el 8501 | `streamlit run app.py --server.port 8502` |
| Los cambios de colores o datos no se ven | El tema y el catálogo se cargan al arrancar | Parar con Ctrl + C y volver a lanzar Streamlit |
| "No tengo 'X' en mi catálogo" | Ese alimento no está entre los 121 | Elegir otro o añadirlo (capítulo 16) |
| "'pollo' coincide con varios alimentos" | Hay pechuga y muslo crudos | Es correcto: MILO pide concretar (o Gemini elige uno de la lista) |
| Una receta sale `pending` | Ingrediente desconocido, estado distinto o nutrientes ausentes | Ver el motivo que imprime `prepare_recipes.py` |
| El notebook no encuentra el kernel | No se eligió el Python de `.venv` | Seleccionar el kernel `.venv` |

---

## 18. Guía para defender el proyecto

### Plan de 8–9 minutos

| Tiempo | Qué enseño | Qué abro |
|---|---|---|
| 1 min | Qué es MILO y qué problema resuelve | Diapositivas 1–2 (`presentacion/MILO_presentacion.html`) |
| 3 min | El RAG con la frase central, paso a paso | Notebook, secciones 3–8 |
| 1 min | El system prompt: dónde está y por qué está así | `src/milo/prompts/system.md` y README §6 |
| 1 min | LangGraph y la memoria | Notebook, secciones 9–10 |
| 3 min | Demo en vivo | `streamlit run app.py` |
| 30 s | Pruebas y limitaciones | Diapositiva 11 |

### Qué conceptos explicar

RAG (buscar antes de responder), embedding (significado como números), ChromaDB (dónde se guardan), agente (decide y
usa herramientas), LangGraph (los pasos como grafo), memoria (checkpointer por `thread_id`) y la regla de diseño
principal: **el RAG busca conocimiento y Python hace las cuentas**.

### Cómo mostrar cada parte

- **RAG**: en el notebook, la tabla de fragmentos por documento (§4), la similitud coseno (§5), el registro guardado en
  Chroma (§6), la tabla de recuperación (§7) y la respuesta con ★ (§8). En la app, el desplegable "Fragmentos
  recuperados de ChromaDB" debajo de cada respuesta.
- **LangGraph**: el diagrama del grafo (§9 del notebook) y, en la app, cómo una pregunta de "nevera" acaba en una ficha
  calculada: eso son las herramientas.
- **Memoria**: en la app, "Soy vegetariano y no me gusta el tomate" → "¿Qué ceno hoy?" (el perfil aparece en la barra
  lateral); o en el notebook §10, el agente "reiniciado" que sigue recordando.
- **Calculadora nutricional**: la ficha de una receta (kcal, proteína, hidratos, grasa) y el ejemplo del bowl de pollo:

  | Ingrediente | Gramos | kcal/100 g | kcal | Proteína |
  |---|---|---|---|---|
  | Pechuga de pollo cruda | 160 | 112,2 | 179,5 | 36,0 g |
  | Arroz blanco seco | 80 | 369,6 | 295,7 | 5,6 g |
  | Tomate roma | 120 | 19,0 | 22,7 | 0,8 g |
  | Aceite de oliva | 10 | 884,0 | 88,4 | 0 g |
  | **Total** | | | **586** | **42,5 g** |

- **Frontend**: las cuatro secciones; Mi nevera y Plan semanal funcionan sin IA (plan B si falla Internet).

### Preguntas probables del profesor

**¿Dónde está el system prompt?** En `src/milo/prompts/system.md`. Lo carga `load_system_prompt()` en `rag.py` y se
envía en cada llamada.

**¿Por qué estos tres documentos?** Uno oficial (AESAN) para recomendaciones fiables y dos propios que necesita la tarea:
el recetario y las técnicas y sustituciones. Suman 83 fragmentos y unas 9.900 palabras.

**¿Qué es un embedding y por qué 3072 dimensiones?** Una lista de números que representa el significado de un texto.
`gemini-embedding-001` genera 3072 números por texto; textos parecidos tienen vectores cercanos.

**¿Cómo sabes que la recuperación funciona?** En el notebook §7 hay consultas de prueba con el documento esperado y una
comprobación automática, y 5 pruebas reales lo verifican.

**¿Por qué no deja que Gemini calcule las calorías?** Porque puede equivocarse con la aritmética y no sería
reproducible. Python suma valores USDA y puedo explicar cada número.

**¿Cómo funciona la memoria?** Checkpointer `SqliteSaver` de LangGraph en `storage/memoria.sqlite`, una conversación
por `thread_id`. Sobrevive a reiniciar.

**¿Cómo evitas recomendar algo que no puedo comer?** El perfil va en el estado del grafo y las herramientas lo reciben de
LangGraph, no de Gemini. `validate_recipe` descarta en Python lo incompatible.

**¿Qué pasa si los documentos no tienen la respuesta?** El prompt le indica decirlo y no inventar fuentes; las cifras
nunca dependen de él.

**¿Qué es `tools_condition`?** Una arista condicional de LangGraph: si Gemini pide una herramienta, el grafo va al nodo
de herramientas; si no, termina.

**¿De dónde salen los alimentos?** De USDA FoodData Central (Foundation 2026 y SR Legacy 2018), con su FDC ID original.
El catálogo se regenera desde los archivos oficiales y las pruebas comparan cada valor.

**¿Qué limitaciones tiene?** 121 alimentos y 36 recetas; macros estimados sin pérdidas de cocción; el menú escala recetas
(no es una dieta clínica); depende de la API de Gemini.

**¿Qué mejorarías?** Más alimentos y recetas, búsqueda híbrida (palabras + vectores), una evaluación sistemática del RAG
con preguntas de referencia y que el usuario pueda guardar recetas propias.

Más detalle de la demo y del texto de cada diapositiva: `presentacion/GUION.md`.

---

## 19. Glosario

| Término | Significado |
|---|---|
| **Agente** | Programa con un modelo de lenguaje que decide pasos y usa herramientas antes de responder |
| **API / API key** | Forma de usar un servicio externo / contraseña personal para usarlo |
| **Arista condicional** | Flecha del grafo que elige el siguiente paso según el estado |
| **Checkpointer** | Componente de LangGraph que guarda el estado tras cada paso (la memoria) |
| **Chunk / fragmento** | Trozo de un documento que se indexa por separado |
| **Cita [n]** | Referencia al fragmento n que respalda una frase |
| **Colección** | El "cajón" de ChromaDB donde se guardan los vectores |
| **CSV / JSON** | Formato de tabla / formato de datos con estructura anidada |
| **Distancia coseno** | Medida de diferencia entre dos vectores (0 = mismo significado) |
| **Embedding** | Vector de números que representa el significado de un texto |
| **FDC ID** | Identificador de un alimento en USDA FoodData Central |
| **Hash SHA-256** | Huella única de un archivo: si cambia un byte, cambia la huella |
| **Herramienta (tool)** | Función de Python que el agente puede pedir ejecutar |
| **LLM** | Modelo de lenguaje grande (Gemini) |
| **Macronutrientes** | Proteína, hidratos de carbono y grasa (y aquí también la fibra) |
| **Nodo** | Paso del grafo de LangGraph |
| **RAG** | Recuperar información de mis documentos y dársela al modelo para que responda con ella |
| **Solapamiento** | Palabras repetidas entre fragmentos consecutivos para no cortar ideas |
| **SQLite** | Base de datos en un solo archivo, sin servidor |
| **System prompt** | Instrucciones fijas que definen el rol y las reglas del asistente |
| **Thread / thread_id** | Identificador de una conversación en la memoria |
| **Token** | Unidad de texto que procesa el modelo (aproximadamente ¾ de palabra) |
| **Vector** | Lista de números |
