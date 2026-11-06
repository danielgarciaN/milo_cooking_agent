# Guía de entrega — MILO

## 1. Qué entrego

| Entregable | Ruta | Qué es |
|---|---|---|
| **Notebook funcional** | `MILO_Proyecto_Final.ipynb` | RAG paso a paso, agente LangGraph, memoria y 6 ejemplos ejecutados |
| **README** | `README.md` | Dominio, instalación, ejecución, arquitectura y justificación del system prompt |
| **System prompt** | `src/milo/prompts/system.md` | Instrucciones de MILO (rol, tono, RAG, herramientas, memoria, seguridad) |
| **Código fuente** | `src/milo/`, `app.py`, `scripts/` | Gemini, RAG, ChromaDB, LangGraph, memoria, herramientas e interfaz |
| **Documentos del RAG** | `data/documents/` | Guía AESAN (PDF), recetario de MILO y técnicas y sustituciones |
| **Datos nutricionales** | `data/foods.csv`, `data/recipes.json`, `data/sources.json` | 121 alimentos USDA, 36 recetas y procedencia de las fuentes |
| **Presentación** | `presentacion/MILO_presentacion.html` | 12 diapositivas (abrir en el navegador; flechas para avanzar) |
| **Guion y preguntas** | `presentacion/GUION.md` | Texto de cada diapositiva, demo y posibles preguntas del profesor |
| **Bonus: Streamlit** | `app.py` | App con chat, Mi nevera, Plan semanal y Mi perfil |
| **Bonus: URL pública** | *pendiente* | Ver el apartado 4 |
| Manual (uso personal) | `MANUAL_DEL_PROYECTO.md` | Explicación completa para principiantes |
| Checklist | `PROJECT_CHECKLIST.md` | Estado verificado de cada requisito |

**No entregar**: `.env` (contiene la clave), `.venv/` ni `storage/` (se regeneran).
Si la entrega es un ZIP, lo creo desde la carpeta del proyecto excluyendo esas tres carpetas/archivos y los ZIP de
`data/usda/` (pesan mucho y se descargan con `python scripts/download_sources.py`).

## 2. Cómo comprobar que todo funciona (5 minutos)

```powershell
.venv\Scripts\Activate.ps1
python -m pytest                    # → 92 passed (sin gastar API)
python scripts/build_index.py       # → Vectores guardados ...: 83
python -m pytest --live             # → 98 passed (usa Gemini; tarda ~2 min)
python scripts/run_notebook.py      # → {"errors": 0}
streamlit run app.py                # → http://localhost:8501
```

## 3. Cómo ejecutar la demo

1. `streamlit run app.py` unos minutos antes y hacer una pregunta de prueba.
2. Pulsar **Nueva conversación**.
3. Seguir el guion de `presentacion/GUION.md` (apartado "Guion de la demo").
4. Plan B si falla Internet o Gemini: el notebook ya tiene todas las salidas reales guardadas; Mi nevera y Plan semanal
   funcionan sin IA.

## 4. Despliegue público en Streamlit Community Cloud (bonus)

El código ya está preparado: lee la clave de *Secrets*, instala todo desde `requirements.txt` y, como `storage/` no se
sube a GitHub, construye el índice de ChromaDB automáticamente la primera vez que arranca (83 embeddings).

Pasos (necesitan mi cuenta de GitHub y de Streamlit):

1. Subir el repositorio a GitHub (`https://github.com/danielgarciaN/milo_cooking_agent`). Comprobar antes con
   `git status` que **no** aparece `.env`.
2. Entrar en <https://share.streamlit.io> con GitHub → **Create app** → elegir el repositorio, rama y archivo `app.py`.
3. En **Advanced settings**: Python 3.12 y en *Secrets* escribir:
   ```toml
   GOOGLE_API_KEY = "mi-clave-de-gemini"
   ```
4. **Deploy**. La primera carga tarda un par de minutos (instalación + índice).
5. Copiar la URL pública en el README (apartado de cabecera) y en la entrega.

Nota: en Streamlit Cloud la memoria (`storage/memoria.sqlite`) dura mientras la app esté encendida; si la plataforma
la reinicia, las conversaciones empiezan de nuevo. En local la memoria es permanente.