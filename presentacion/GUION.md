# Guion de la presentación (8–9 minutos)

Diapositivas: abrir `presentacion/MILO_presentacion.html` en el navegador (pantalla completa con F11).
Avanzar con → o clic; retroceder con ←.

## Antes de empezar (checklist)

- [ ] `.venv` activado y `streamlit run app.py` ya arrancado en otra ventana (la primera carga tarda unos segundos).
- [ ] Hacer una pregunta de calentamiento en la app para comprobar la conexión con Gemini.
- [ ] Notebook `MILO_Proyecto_Final.ipynb` abierto con las salidas ya ejecutadas (es el plan B).
- [ ] Pulsar "Nueva conversación" en la app para empezar la demo limpia.

## Diapositivas y texto

**1 · Portada (20 s).** "Este es MILO, un pequeño chef digital. Es un asistente de cocina y nutrición construido con
Gemini, RAG sobre ChromaDB y un agente de LangGraph con memoria."

**2 · El problema (40 s).** "Todos nos hemos preguntado qué cocinar con lo que hay en la nevera y cuántas calorías tiene.
MILO recomienda recetas con lo que tengo, calcula macros con datos reales, organiza la semana, sustituye ingredientes,
responde con una guía oficial citándola y recuerda lo que le cuento."

**3 · La frase central (40 s).** Leer la frase. "Todo el proyecto está organizado alrededor de esta secuencia y en el
notebook enseño cada paso con datos reales."

**4 · Documentos y chunking (50 s).** "Uso tres documentos: la guía oficial de AESAN, mi recetario de 28 recetas y una
guía de técnicas y sustituciones. Los divido por títulos en fragmentos de hasta 400 palabras. Una decisión que aprendí
probando: el índice del PDF salía como primer resultado de casi todo, así que quito portada, índice y contraportada."

**5 · Embeddings, Chroma y recuperación (50 s).** "Cada fragmento se convierte en un vector de 3072 números con Gemini
Embeddings y se guarda en ChromaDB. Si pregunto cuántos huevos puedo comer, la búsqueda devuelve la página 9 de AESAN,
que dice exactamente 'máximo 4 huevos a la semana'. Busco por significado, no por palabras."

**6 · RAG vs Python (50 s).** "La decisión más importante: el RAG busca conocimiento, pero las cuentas las hace Python.
Los LLM no son fiables con la aritmética. Las calorías salen de los valores USDA por 100 g multiplicados por los gramos.
Aquí está el bowl de pollo: 586 kcal y 42,5 g de proteína, y puedo explicar de dónde sale cada número."

**7 · LangGraph (50 s).** "El agente es un grafo de tres nodos: recuperar busca en ChromaDB en cada turno; milo es
Gemini, que decide si responde o usa una herramienta; y herramientas ejecuta Python. Tiene ocho herramientas: recetas,
sustituciones, platos libres, menú semanal, lista de la compra, perfil y búsqueda extra en documentos."

**8 · System prompt (40 s).** "El prompt está en un archivo propio. Define rol, personalidad, uso de documentos y
herramientas, memoria y seguridad. Lo iteré con pruebas reales: por ejemplo, Gemini citaba un fragmento del salmón en una
receta de huevos que venía de Python, así que añadí que las cifras de herramientas no se citan."

**9 · Memoria (40 s).** "La memoria es un checkpointer SQLite de LangGraph: una conversación por thread_id. En el
notebook creo un agente nuevo y sigue recordando que soy vegetariano. Otra conversación no ve nada."

**10 · Demo en vivo (3 min).** Cambiar a la app. Ver el guion de la demo abajo.

**11 · Calidad y límites (30 s).** "92 pruebas automáticas, 6 más con Gemini real, el notebook se ejecuta entero sin
errores y las 28 recetas están validadas. Limitaciones: catálogo de 70 alimentos, macros estimados y depende de la API."

**12 · Gracias (10 s).**

## Guion de la demo (3 minutos)

1. **Chat → sugerencia** "¿Qué recomienda la documentación sobre una alimentación equilibrada?"
   Abrir "📚 Fragmentos recuperados de ChromaDB": "aquí se ve qué ha recuperado y qué ha citado Gemini".
2. Escribir: **"Tengo pollo, arroz, aguacate y huevos. Quiero una cena de unas 800 kcal y bastante proteína."**
   Señalar la ficha: "estas cifras las ha calculado Python, no Gemini".
3. Escribir: **"Soy vegetariano y no me gusta el tomate."** → **"¿Qué ceno hoy?"**. Señalar en la barra lateral
   "Tu perfil: dieta vegetariana; no le gusta: tomate".
4. **Plan semanal** → Generar menú → enseñar el gráfico y la lista de la compra (funciona sin IA).
5. Si sobra tiempo: **Mi nevera** con pollo, arroz y huevo → "Ver receta".

**Si Gemini falla durante la demo:** "Gemini a veces se satura; tengo reintentos y un modelo de respaldo, y si aun así
falla, aquí está el notebook con las salidas reales" → enseñar las secciones 10 y 11 del notebook. Mi nevera y Plan
semanal funcionan igualmente porque no usan IA.

## Preguntas probables del profesor

**¿Por qué estos tres documentos?** Uno oficial (AESAN) para recomendaciones fiables, y dos propios que el asistente
necesita para su tarea: el recetario y las técnicas/sustituciones. Suman unas 30 páginas equivalentes y 75 fragmentos.

**¿Por qué 400 palabras y 50 de solapamiento?** Las secciones de la guía y las recetas suelen caber en un fragmento, así
cada fragmento trata un tema completo. El solapamiento evita perder una frase cuando una sección larga se corta.

**¿Qué modelo de embeddings y por qué?** `gemini-embedding-001` con 3072 dimensiones: es el modelo de embeddings de
Gemini que exige el enunciado y funciona bien en español. Si lo cambiara, el nombre de la colección cambia y se reindexa.

**¿Cómo sabes que la recuperación funciona?** En el notebook (sección 7) hay tres consultas de prueba con documento
esperado y una aserción; además hay 5 tests `--live` que comprueban la fuente recuperada y que Gemini cita.

**¿Qué pasa si los documentos no tienen la respuesta?** El prompt le indica decirlo ("mis documentos no tratan eso") y no
inventar fuentes. Las cifras nunca dependen de él porque vienen de Python.

**¿Por qué no dejar que Gemini calcule las calorías?** Porque puede equivocarse con la aritmética y no sería
reproducible. Con Python el mismo plato da siempre el mismo resultado y puedo explicarlo ingrediente a ingrediente.

**¿Cómo funciona la memoria y dónde se guarda?** Checkpointer `SqliteSaver` en `storage/memoria.sqlite`, una
conversación por `thread_id`. Guarda mensajes, perfil y resultados de herramientas. Envío a Gemini los 8 últimos turnos.

**¿Cómo evitas recomendar algo que el usuario no puede comer?** El perfil se guarda en el estado y las herramientas lo
reciben de LangGraph (`InjectedState`), no de Gemini. `validate_recipe` en Python descarta recetas por dieta, alérgenos
o alimentos que no gustan. Si hay alergias, tampoco recomiendo productos comerciales cuya composición depende de la marca.

**¿Qué es `tools_condition`?** Una arista condicional de LangGraph: si el último mensaje de Gemini pide una herramienta,
el grafo va al nodo de herramientas; si no, termina.

**¿Por qué recuperar en cada turno aunque no haga falta?** El enunciado pide usar la base de conocimiento en cada consulta
y así las respuestas siempre tienen contexto. Si la pregunta es muy corta añado la anterior para que la búsqueda tenga sentido.

**¿Qué limitaciones tiene?** 70 alimentos y 28 recetas, macros estimados sin pérdidas de cocción, el menú escala recetas
(no es un optimizador) y depende de la API de Gemini.

**¿Cómo lo desplegarías?** Streamlit Community Cloud con la clave en *Secrets*. El índice de Chroma se construye solo al
arrancar la primera vez.

**¿Qué mejorarías?** Más alimentos y recetas, búsqueda híbrida, una evaluación sistemática del RAG con preguntas de
referencia y que el usuario pueda guardar sus propias recetas.
