# Manual del proyecto MILO

Este manual explica MILO desde cero: qué es, qué piezas tiene, dónde está cada cosa, cómo funciona por dentro, cómo
ejecutarlo, cómo modificarlo y qué enseñar en la defensa. Está pensado para leerse sin saber casi nada de agentes.

**Índice**
1. Qué es MILO · 2. Tecnologías · 3. Carpetas y archivos · 4. Cómo funciona el RAG · 5. Cómo funciona LangGraph ·
6. Cómo se calculan los macros · 7. Cómo funciona la memoria · 8. Cómo funciona Streamlit · 9. Ejecutar MILO desde cero ·
10. Cómo modificarlo · 11. Problemas habituales · 12. Qué enseñar al profesor · 13. Glosario

---

## Capítulo 1 — Qué es MILO

MILO (*AI Nutrition Chef*) es un asistente de inteligencia artificial de cocina y nutrición con personalidad de
pequeño chef. Su mascota es una criatura con gorro de cocinero, delantal crema y cuchara de madera.

**Problema que resuelve.** Mucha gente no sabe qué cocinar con lo que tiene, cómo ajustar una receta a un objetivo de
calorías o cómo organizar las comidas de la semana.

**Qué puede hacer.**
- Responder preguntas de alimentación saludable usando una guía oficial (AESAN) y citando la fuente.
- Recomendar recetas según lo que hay en la nevera, el tiempo, las calorías o la proteína.
- Calcular calorías y macronutrientes con datos reales de USDA.
- Ajustar una receta a unas kcal o a varias raciones.
- Sustituir un ingrediente y recalcular.
- Crear un menú de hasta 7 días y su lista de la compra.
- Recordar el perfil (vegetariano, alergias, alimentos que no gustan, objetivo) y la conversación.

**La idea más importante:** *el RAG busca conocimiento y Python hace las cuentas*. Gemini redacta las respuestas,
pero nunca inventa una caloría.

---

## Capítulo 2 — Tecnologías

| Tecnología | Qué es | Para qué la uso | Dónde aparece |
|---|---|---|---|
| **Python** | Lenguaje de programación | Todo el proyecto | `src/milo/`, `app.py`, `scripts/` |
| **Gemini** | Familia de modelos de IA de Google | Redactar respuestas y decidir qué herramienta usar | `rag.py` → `create_model` |
| **API key** | Contraseña personal para usar Gemini | Autentica mis llamadas. Nunca va en el código | Archivo `.env` (no se sube a GitHub) |
| **Embeddings** | Listas de números que representan el significado de un texto | Comparar una pregunta con mis documentos | `rag.py` → `create_embeddings` (`gemini-embedding-001`) |
| **RAG** | *Retrieval-Augmented Generation*: buscar información y dársela al LLM para que responda | Que MILO responda con mis documentos y no de memoria | `rag.py` |
| **ChromaDB** | Base de datos de vectores | Guardar los embeddings y buscar los más parecidos | Carpeta `storage/chroma` |
| **LangChain** | Librería que unifica modelos, mensajes y herramientas | Conectar Gemini, Chroma y las herramientas | `langchain_google_genai`, `langchain_chroma` |
| **LangGraph** | Librería para construir agentes como grafos de pasos | El agente: recuperar → pensar → usar herramientas | `agent.py` |
| **Memoria** | Guardar el estado de la conversación | Recordar preferencias y "la receta anterior" | `SqliteSaver` → `storage/memoria.sqlite` |
| **Streamlit** | Librería para crear webs con Python | La app de chat, nevera, plan y perfil | `app.py`, `.streamlit/config.toml` |
| **Jupyter Notebook** | Documento con texto y código ejecutable | La demostración paso a paso para el profesor | `MILO_Proyecto_Final.ipynb` |
| **Pydantic** | Validación de datos | Que un peso negativo o un alimento sin datos no pase | `models.py` |
| **pytest** | Pruebas automáticas | Comprobar que nada se rompe | `tests/` |

---

## Capítulo 3 — Carpetas y archivos

### Raíz

| Archivo | Qué contiene / para qué sirve | ¿Lo puedo modificar? | Si lo borro… |
|---|---|---|---|
| `MILO_Proyecto_Final.ipynb` | Notebook de entrega: RAG paso a paso, agente, memoria y ejemplos | Sí, sus explicaciones | Pierdo el entregable principal |
| `app.py` | La app de Streamlit (solo pantallas: importa el agente) | Sí: textos, colores, secciones | No hay interfaz web |
| `README.md` | Resumen de entrega: instalación, RAG, justificación del prompt | Sí | Falta un entregable |
| `MANUAL_DEL_PROYECTO.md` | Este manual | Sí | — |
| `PROJECT_CHECKLIST.md` | Requisitos y su estado verificado | Sí | — |
| `ENTREGA_FINAL.md` | Qué entregar y cómo comprobarlo | Sí | — |
| `requirements.txt` | Librerías necesarias | Con cuidado | No se puede instalar |
| `requirements-lock.txt` | Versiones exactas con las que lo probé | No hace falta | Pierdo la referencia de versiones |
| `pyproject.toml` | Define el paquete `milo` y la configuración de pytest/ruff | Con cuidado | `pip install -e .` deja de funcionar |
| `.env.example` | Plantilla de configuración sin clave | Sí | — |
| `.env` | **Mi clave de Gemini** (privado, ignorado por git) | Sí | MILO no puede llamar a Gemini |
| `.gitignore` | Lo que nunca se sube (clave, entorno, índice) | Con cuidado | Podría subir mi clave |
| `.streamlit/config.toml` | Tema de la app: colores y fuente | Sí | La app vuelve al estilo por defecto |
| `LICENSE` | Licencia MIT | No | — |

### `src/milo/` — el código de MILO

| Archivo | Qué hace | Cuándo se usa |
|---|---|---|
| `config.py` | Rutas de archivos y lectura de `.env` (clave y modelos) | Siempre |
| `models.py` | "Moldes" de datos: alimento, ingrediente, receta, perfil, fragmento. Validan que todo sea coherente | Siempre |
| `nutrition.py` | Catálogo de alimentos (búsqueda por nombre) y **calculadora** de macros, validación de restricciones y escalado | Cada cálculo |
| `recipes.py` | Clase `Kitchen`: buscar recetas, nevera, ver/escalar, sustituir, plato libre, plan semanal, lista de la compra y perfil | Herramientas del agente y páginas de la app |
| `rag.py` | Todo el RAG: leer documentos, chunking, embeddings, ChromaDB, recuperar y generar | Notebook, agente y app |
| `agent.py` | Grafo LangGraph, las 8 herramientas y la memoria | Chat del notebook, terminal y app |
| `usda.py` | Importa los alimentos de los ZIP oficiales de USDA | Solo al regenerar `foods.csv` |
| `prompts/system.md` | **El system prompt de MILO** | En cada llamada a Gemini |

### `data/` — los datos

| Ruta | Qué es | Notas |
|---|---|---|
| `data/documents/aesan_recomendaciones_dieteticas_2022.pdf` | Documento 1 del RAG: guía oficial AESAN | No editar (su hash está registrado) |
| `data/documents/recetario_milo.md` | Documento 2: recetario. **Se genera** desde `recipes.json` | No editar a mano: usar `scripts/prepare_recipes.py` |
| `data/documents/tecnicas_y_sustituciones.md` | Documento 3: técnicas y sustituciones | Si lo edito, ejecutar `prepare_recipes.py` para registrar el hash |
| `data/foods.csv` | 70 alimentos con kcal, proteína, hidratos, grasa y fibra **por 100 g**, alérgenos y si son veganos/vegetarianos | La calculadora lo usa siempre. Se regenera con `scripts/build_catalog.py` |
| `data/recipes.json` | 28 recetas con ingredientes en gramos, pasos, tiempo y tipo de comida | Aquí se añaden recetas |
| `data/sources.json` | Procedencia de cada fuente: URL, versión, tamaño, hash SHA-256, páginas omitidas | Si lo borro, el RAG no sabe qué documentos indexar |
| `data/usda/` | Qué alimentos elegí de USDA (`seleccion_*.json`) y los ZIP oficiales | Los ZIP no se suben a GitHub; se descargan con `scripts/download_sources.py` |

### `scripts/` — utilidades

| Script | Para qué |
|---|---|
| `build_index.py` | Crear o reconstruir el índice ChromaDB (`--rebuild` borra y crea de cero; `--dry-run` solo cuenta fragmentos) |
| `chat.py` | Conversar con MILO en la terminal (`--rag` solo RAG, `--hilo nombre` retoma una conversación) |
| `prepare_recipes.py` | Validar `recipes.json` y regenerar `recetario_milo.md` |
| `run_notebook.py` | Ejecutar el notebook completo de principio a fin |
| `build_catalog.py` | Regenerar `foods.csv` desde los ZIP de USDA |
| `download_sources.py` | Descargar y verificar las fuentes oficiales |

### Otras carpetas

| Carpeta | Qué es | Si la borro… |
|---|---|---|
| `storage/` | Generada: `chroma/` (índice vectorial) y `memoria.sqlite` (conversaciones). No se sube a git | Se regenera sola; pierdo las conversaciones guardadas |
| `tests/` | 92 pruebas sin API y 6 con Gemini real | Pierdo la verificación automática |
| `assets/` | `milo.png` (mascota original) y `milo_small.png` (versión ligera para la app) | La app no muestra la mascota |
| `presentacion/` | Diapositivas (`MILO_presentacion.html`) y guion (`GUION.md`) | — |
| `.venv/` | Entorno virtual con las librerías instaladas | Hay que reinstalar |

---

## Capítulo 4 — Cómo funciona el RAG

> **"Estos son mis tres documentos. Así los divido. Así los convierto en vectores. Aquí los guardo. Cuando pregunto
> algo, estos son los fragmentos que recupera. Y esta es la respuesta que genera Gemini utilizando esa información."**

**1. "Estos son mis tres documentos."** Están en `data/documents/` y registrados en `data/sources.json`
(`usage: "rag_general"`). La función `rag_sources()` los localiza y `check_source()` comprueba su huella SHA-256: si
el archivo no coincide con el registro, el proceso se para (así sé que el índice corresponde a los documentos actuales).

**2. "Así los divido."** `load_documents()` lee el PDF página a página con `pypdf` y los Markdown completos. Después:
- `clean_text()` arregla el texto del PDF: une palabras cortadas con guion y la ligadura "ﬁ" ("refi nadas" → "refinadas").
- `split_sections()` separa por títulos (`## ...` o líneas en MAYÚSCULAS).
- `chunk_page()` corta cada sección en fragmentos de hasta 400 palabras, con 50 de solapamiento si es larga.
- Del PDF omito las páginas 1, 2 y 19 (portada, índice y contraportada): en una primera versión el índice salía como
  primer resultado de casi todas las búsquedas.

Resultado: **75 fragmentos** (35 de AESAN, 29 del recetario y 11 de técnicas). Cada uno guarda su documento, su página
(PDF) o sección (Markdown), su versión y un identificador estable.

**3. "Así los convierto en vectores."** `create_embeddings()` usa `gemini-embedding-001`. Cada fragmento se convierte en
un vector de 3072 números. Textos con significado parecido tienen vectores parecidos (en el notebook lo compruebo con la
similitud coseno: "¿cuántos huevos puedo comer?" se parece mucho más a la frase de AESAN sobre huevos que a una frase
sobre el agua).

**4. "Aquí los guardo."** `index_chunks()` guarda en ChromaDB (carpeta `storage/chroma`) el texto, el vector y los
metadatos. El nombre de la colección depende del modelo y de los fragmentos: si cambio un documento se crea una
colección nueva y nunca mezclo vectores viejos. Solo se calculan los embeddings que faltan.

**5. "Cuando pregunto algo, estos son los fragmentos que recupera."** `NutritionRAG.retrieve()` convierte la pregunta en
vector y pide a Chroma los 4 más cercanos (distancia coseno: menor = más parecido). Ejemplo real:
"¿Cuántos huevos puedo comer a la semana?" → primer resultado `AESAN_2022 — página 9` ("máximo de 4 huevos medianos a
la semana"), distancia ≈ 0,22.

**6. "Y esta es la respuesta que genera Gemini."** `NutritionRAG.generate()` envía a Gemini el system prompt y un
mensaje con los fragmentos numerados entre `<documentos>`. Gemini responde citando `[1]`, `[2]`. La función
`cited_numbers()` detecta qué fragmentos ha citado y en el notebook se marcan con ★.

---

## Capítulo 5 — Cómo funciona LangGraph

Un **grafo** es una serie de pasos (nodos) conectados por flechas. El estado de la conversación pasa de nodo en nodo.

```text
START → recuperar → milo ──(¿pide herramienta?)── sí → herramientas ─┐
                     ▲                                               │
                     └───────────────────────────────────────────────┘
                     └── no → END
```

**Estado** (`MiloState` en `agent.py`): `messages` (historial), `profile` (perfil) y `fragments` (fragmentos del turno).

**Nodo `recuperar`** (`MiloAgent.retrieve`): busca en ChromaDB con la última pregunta. Si tiene menos de 6 palabras
("¿y cuántas calorías tiene?"), le pega la pregunta anterior para que la búsqueda tenga sentido.

**Nodo `milo`** (`MiloAgent.call_model`): monta el mensaje de sistema = system prompt + resumen del perfil + fragmentos,
y se lo envía a Gemini junto a los últimos 8 turnos. Gemini tiene "atadas" las herramientas (`bind_tools`): puede
contestar con texto o con una **petición de herramienta** (nombre + argumentos).

**Arista condicional** (`tools_condition`): si el mensaje de Gemini pide una herramienta, va a `herramientas`; si no, termina.

**Nodo `herramientas`** (`ToolNode`): ejecuta la función Python pedida y devuelve el resultado a Gemini como un mensaje
de herramienta. Vuelve al nodo `milo`, que puede pedir otra herramienta o redactar la respuesta final. Si una herramienta
lanza un error (por ejemplo, un alimento que no existe), el error se le devuelve a Gemini para que lo corrija.

**Ejemplo real** — "Tengo pollo, arroz, aguacate y huevos. Quiero una cena de unas 800 kcal":
1. `recuperar` trae las recetas r023, r001, r007 y r024.
2. `milo` pide `buscar_recetas(ingredientes=[pollo, arroz, aguacate, huevos])` → Python devuelve recetas con lo que
   tienes y lo que falta.
3. `milo` pide `ver_receta(recipe_id="r001", objetivo_kcal=800)` → Python escala el bowl a 800 kcal y calcula los macros.
4. `milo` redacta la respuesta con esos números.

**Ejemplo de sustitución** — "No tengo aguacate, ¿por qué lo sustituyo en las tostadas?": Gemini no conoce los 70
alimentos del catálogo, así que llama a `sustituir_ingrediente` sin sustituto. Python devuelve 4 alternativas que sí
existen, compatibles con el perfil, cuya energía se reparte de forma parecida entre proteína, hidratos y grasa (nueces,
almendras…), cada una con la cantidad equivalente en energía y los macros de la receta resultante.

Las **8 herramientas** están en `make_tools()` (`agent.py`); cada una llama a un método de `Kitchen` (`recipes.py`). Su
*docstring* es la descripción que lee Gemini para decidir cuándo usarla. Los parámetros marcados con `InjectedState`
(el perfil, el historial) los rellena LangGraph, no Gemini: así el modelo no puede "olvidarse" de las restricciones.

---

## Capítulo 6 — Cómo se calculan los macros

`data/foods.csv` tiene los valores **por 100 g** de cada alimento (de USDA). Para un ingrediente:

```
aporte = valor por 100 g × gramos / 100
```

Ejemplo real con la receta **r001 — Bowl de pollo y arroz** (1 ración):

| Ingrediente | Gramos | kcal/100 g | kcal aportadas | Proteína/100 g | Proteína aportada |
|---|---|---|---|---|---|
| Pechuga de pollo cruda | 160 | 112,2 | 179,5 | 22,5 g | 36,0 g |
| Arroz blanco seco | 80 | 369,6 | 295,7 | 7,0 g | 5,6 g |
| Tomate roma crudo | 120 | 19,0 | 22,7 | 0,7 g | 0,8 g |
| Aceite de oliva | 10 | 884,0 | 88,4 | 0 g | 0 g |
| **Total** | | | **586 kcal** | | **42,5 g** |

- **Suma**: `calculate_nutrition()` suma ingrediente a ingrediente (con decimales exactos, `Decimal`).
- **Raciones**: divide el total entre las raciones. Con `ver_receta(raciones=2)` se duplican los gramos: 1.173 kcal en
  total y 586 por ración.
- **Escalar a unas kcal**: `adjust_portions()` calcula un factor (800 / 586 ≈ 1,37) y multiplica todos los gramos.
- **Pesos crudos y cocinados**: cada ingrediente tiene un estado (crudo, seco, escurrido, cocinado). 80 g de arroz seco
  no son 80 g de arroz cocido, y el código no deja mezclarlos.
- **Datos ausentes**: si un alimento no publica fibra en USDA, el total de fibra queda "sin dato". Nunca se rellena con 0.
- **Restricciones**: `validate_recipe()` comprueba dieta, alérgenos y alimentos que no gustan.

---

## Capítulo 7 — Cómo funciona la memoria

- **Qué se recuerda**: todos los mensajes (usuario, Gemini y resultados de herramientas), el perfil y los fragmentos del
  último turno. Por eso funciona "la receta anterior" o "la lista de la compra de ese menú" (la herramienta
  `lista_compra` busca el último menú en el historial).
- **Dónde se guarda**: en `storage/memoria.sqlite`, mediante el checkpointer `SqliteSaver` de LangGraph. Cada
  conversación tiene un `thread_id`.
- **Cuánto dura**: hasta que borre ese archivo. Sobrevive a cerrar Python o reiniciar el ordenador.
- **Otra conversación**: con otro `thread_id` empieza vacía y no ve nada de las demás. En la app, el identificador va en
  la URL (`?c=...`): si recargo la página, sigue la misma charla; el botón "Nueva conversación" crea otro.
- **Qué se envía a Gemini**: los últimos 8 turnos (para no gastar tokens). El resto sigue guardado.

---

## Capítulo 8 — Cómo funciona Streamlit

- **Archivo de arranque**: `app.py` (`streamlit run app.py`). El tema (colores y fuente Nunito) está en `.streamlit/config.toml`.
- **Recursos compartidos**: `load_agent()` crea un único `MiloAgent` y `load_kitchen()` una única `Kitchen`
  (`@st.cache_resource`), así no se recargan en cada clic.
- **Sesión**: `st.session_state` guarda el `thread_id`, el perfil, los turnos mostrados y el último menú.
- **Chat**: `st.chat_input` recibe el mensaje → `ask_milo()` llama a `agent.ask(pregunta, thread_id, profile)` → se
  guarda la respuesta y sus resultados. Se dibuja con `st.chat_message`: el texto de Gemini, las fichas calculadas por
  Python (`recipe_card`, `plan_view`, `shopping_view`) y un desplegable con los fragmentos de ChromaDB (`sources_view`).
- **Mi nevera** y **Plan semanal** llaman directamente a `Kitchen` (sin IA): son instantáneas y funcionan aunque Gemini
  falle. Desde la nevera puedo pasar la pregunta al chat con un botón.
- **Mi perfil** es un formulario; el perfil se envía al agente en la siguiente pregunta. Si en el chat digo "soy
  vegetariano", la herramienta `guardar_perfil` lo actualiza y la app lo sincroniza.
- **Errores**: si falta la clave o Gemini está saturado, se muestra un mensaje comprensible en el chat.

---

## Capítulo 9 — Cómo ejecutar MILO desde cero (Windows, PowerShell)

1. **Abrir la carpeta**: en VS Code, *Archivo → Abrir carpeta* → `milo_cooking_agent`. Abrir una terminal
   (*Terminal → Nueva terminal*), que será PowerShell.
2. **Crear el entorno virtual** (solo la primera vez):
   ```powershell
   python -m venv .venv
   ```
3. **Activarlo** (cada vez que abro una terminal):
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
   Si PowerShell lo bloquea: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y repetir.
   Al activarse, la línea empieza por `(.venv)`.
4. **Instalar dependencias** (solo la primera vez):
   ```powershell
   python -m pip install -r requirements.txt
   ```
5. **Configurar la API key**:
   ```powershell
   copy .env.example .env
   notepad .env
   ```
   Escribir la clave después de `GOOGLE_API_KEY=` y guardar.
6. **Preparar ChromaDB** (opcional: si no lo hago, se crea solo la primera vez):
   ```powershell
   python scripts/build_index.py
   ```
   Debe terminar con `Vectores guardados ...: 75`.
7. **Ejecutar el notebook**: abrir `MILO_Proyecto_Final.ipynb`, elegir el kernel de `.venv` (arriba a la derecha) y
   pulsar *Run All*. O en la terminal: `python scripts/run_notebook.py`.
8. **Agente por terminal**:
   ```powershell
   python scripts/chat.py
   ```
   Escribir preguntas; `salir` para terminar.
9. **App Streamlit**:
   ```powershell
   streamlit run app.py
   ```
   Se abre <http://localhost:8501> en el navegador.
10. **Detener la app**: en la terminal, `Ctrl + C`.

Comprobar que todo está bien: `python -m pytest` (debe decir `92 passed`).

---

## Capítulo 10 — Cómo modificarlo

**Añadir una receta.** Añadir un objeto a `data/recipes.json` copiando una existente: `recipe_id` nuevo (`r029`),
`title`, `servings`, `ingredients` (cada uno con `food_id` de `data/foods.csv`, `grams` y el mismo `state` que tiene ese
alimento en el catálogo), `steps`, `time_minutes_estimate`, `difficulty` (`fácil` o `media`) y `tags`
(`desayuno`, `comida`, `cena`, `snack`). Después:
```powershell
python scripts/prepare_recipes.py   # valida y regenera recetario_milo.md
python scripts/build_index.py       # indexa el recetario actualizado
```
Si la receta sale `pending`, el script imprime el motivo (por ejemplo, un `food_id` inexistente).

**Añadir un alimento.** Los alimentos vienen de USDA para no inventar valores. Buscar el alimento en
<https://fdc.nal.usda.gov/>, añadir su FDC ID y nombre en español al archivo de selección correspondiente de
`data/usda/` y ejecutar `python scripts/download_sources.py` y `python scripts/build_catalog.py`.

**Añadir otro PDF al RAG.** Copiarlo a `data/documents/`, añadir una entrada en `data/sources.json` con
`"usage": "rag_general"`, `"file_type": "pdf"`, su `path`, `url`, `version` y su `sha256`
(`Get-FileHash archivo.pdf -Algorithm SHA256` en PowerShell, en minúsculas) y `size_bytes`. Después
`python scripts/build_index.py`.

**Reconstruir ChromaDB.** `python scripts/build_index.py --rebuild`.

**Cambiar el system prompt o la personalidad.** Editar `src/milo/prompts/system.md`. No hace falta reindexar; basta con
reiniciar la app o el kernel del notebook.

**Cambiar colores.** En `.streamlit/config.toml` (colores base del tema) y en las constantes `ORANGE`, `CREAM`, `GREEN`,
`CHARCOAL` del principio de `app.py` (tarjetas y gráficos).

**Cambiar la mascota.** Sustituir `assets/milo.png` y `assets/milo_small.png` (la app usa la pequeña).

**Añadir una herramienta.** 1) Programar la lógica como método de `Kitchen` en `recipes.py`. 2) En `make_tools()` de
`agent.py`, crear una función con `@tool(response_format="content_and_artifact")`, una docstring clara (es lo que lee
Gemini) y que devuelva `(texto_json, resultado)`. 3) Añadirla a la lista que devuelve `make_tools()`. 4) Mencionarla en la
sección "Cómo usar las herramientas" del system prompt. 5) Añadir un test en `tests/test_recipes.py`.

---

## Capítulo 11 — Problemas habituales

| Problema | Causa | Solución |
|---|---|---|
| `Falta GOOGLE_API_KEY` | No existe `.env` o la clave está vacía | `copy .env.example .env` y escribir la clave |
| `503 UNAVAILABLE` / "Gemini está saturado" | Demanda alta en Google | MILO reintenta y usa el modelo de respaldo; esperar unos segundos y repetir |
| `429` / cuota superada | Límite de la capa gratuita | Esperar un minuto; MILO ya limita a 15 llamadas/min |
| `El documento X ha cambiado y no coincide con sources.json` | Se editó un documento sin registrar su hash | `python scripts/prepare_recipes.py` (documentos propios) y `python scripts/build_index.py` |
| ChromaDB vacío o "Falta indexar" | Se borró `storage/` o cambió un documento | `python scripts/build_index.py` (MILO también lo hace solo al arrancar) |
| `ModuleNotFoundError: milo` | No se instaló el paquete o no está activado `.venv` | Activar `.venv` y `python -m pip install -r requirements.txt` |
| `ModuleNotFoundError` de otra librería | Faltan dependencias | `python -m pip install -r requirements.txt` |
| Streamlit no arranca / `streamlit` no se reconoce | Entorno no activado | `.venv\Scripts\Activate.ps1` o `python -m streamlit run app.py` |
| Puerto ocupado | Otra app en el 8501 | `streamlit run app.py --server.port 8502` |
| No encuentra un archivo | La terminal no está en la carpeta del proyecto | `cd` a `milo_cooking_agent` (las rutas internas ya son absolutas) |
| "No tengo 'X' en mi catálogo" | Ese alimento no está entre los 70 de USDA | Elegir otro alimento o añadirlo (capítulo 10) |
| Una receta sale `pending` | Ingrediente desconocido, estado distinto al del catálogo o nutrientes ausentes | Ver el motivo que imprime `prepare_recipes.py` |
| El notebook no encuentra el kernel | No se eligió el Python de `.venv` | Seleccionar el kernel `.venv` en VS Code/Jupyter |

---

## Capítulo 12 — Qué enseñar al profesor

**Orden recomendado (≈ 8 minutos):**
1. **README** (30 s): dominio, arquitectura y la tabla de justificación del system prompt.
2. **Notebook**, secciones 3–8 (3 min): recorrer la frase *"estos son mis tres documentos… así los divido… vectores…
   aquí los guardo… fragmentos que recupera… respuesta de Gemini"*. Enseñar la tabla de fragmentos, la similitud coseno,
   el registro guardado en Chroma, la tabla de recuperación y la respuesta con ★.
3. **`src/milo/prompts/system.md`** (30 s): dónde está y cómo se carga.
4. **Notebook**, secciones 9–10 (1,5 min): el grafo y la memoria (incluida la demostración tras "reiniciar").
5. **App Streamlit en vivo** (2–3 min): hacer 2–3 preguntas y abrir "Fragmentos recuperados de ChromaDB"; enseñar
   Mi nevera y el Plan semanal con la lista de la compra.

**Preguntas para la demo en vivo:**
- "¿Qué recomienda la documentación sobre una alimentación equilibrada?" (RAG puro, citas)
- "Tengo pollo, arroz, aguacate y huevos. Quiero una cena de unas 800 kcal y bastante proteína." (herramientas)
- "Soy vegetariano y no me gusta el tomate." → "¿Qué ceno hoy?" (memoria de perfil)
- "Hazme un menú de 3 días de 2.500 kcal" → "Genera la lista de la compra" (memoria de contexto)
- "¿Cuántos huevos puedo comer a la semana?" (fuente AESAN página 9)

**Plan B** si falla Internet o Gemini: el notebook ya ejecutado muestra todas las salidas reales; Mi nevera y Plan
semanal funcionan sin IA.

Guion completo y preguntas probables del profesor: `presentacion/GUION.md`.

---

## Capítulo 13 — Glosario

| Término | Significado |
|---|---|
| **Agente** | Programa con un LLM que decide pasos y usa herramientas para cumplir una petición |
| **API key** | Clave secreta para usar un servicio (Gemini) |
| **Arista condicional** | Flecha del grafo que elige el siguiente nodo según el estado |
| **Checkpointer** | Componente de LangGraph que guarda el estado tras cada paso (memoria) |
| **Chunk / fragmento** | Trozo de un documento que se indexa por separado |
| **Chunking** | Dividir documentos en fragmentos |
| **Cita [n]** | Referencia al fragmento n que respalda una frase |
| **Colección** | "Tabla" de ChromaDB donde se guardan los vectores |
| **Distancia coseno** | Medida de diferencia entre dos vectores (0 = iguales) |
| **Embedding** | Vector de números que representa el significado de un texto |
| **FDC ID** | Identificador de un alimento en USDA FoodData Central |
| **Hash SHA-256** | Huella única de un archivo; si cambia un byte, cambia la huella |
| **LLM** | Modelo de lenguaje grande (Gemini) |
| **Macronutrientes** | Proteína, hidratos de carbono y grasa (y aquí también la fibra) |
| **Nodo** | Paso del grafo de LangGraph (una función de Python) |
| **Prompt / system prompt** | Instrucciones de texto para el modelo; el system prompt fija su rol y reglas |
| **RAG** | Recuperar información relevante y dársela al LLM para que responda con ella |
| **Solapamiento** | Palabras repetidas entre fragmentos consecutivos para no cortar ideas |
| **Thread / thread_id** | Identificador de una conversación en la memoria |
| **Token** | Unidad de texto que procesa el modelo (≈ ¾ de palabra) |
| **Tool / herramienta** | Función Python que el agente puede pedir ejecutar |
| **Vector** | Lista de números |
