"""Configuración y rutas del proyecto. La clave de Gemini se lee de .env o de las variables de entorno."""

from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"  # Los tres documentos del RAG.
FOODS_CSV = DATA_DIR / "foods.csv"  # 70 alimentos USDA con valores por 100 g.
RECIPES_JSON = DATA_DIR / "recipes.json"  # Recetario estructurado (ingredientes en gramos).
SOURCES_JSON = DATA_DIR / "sources.json"  # Procedencia, versión y hash de cada fuente.
SYSTEM_PROMPT_FILE = Path(__file__).parent / "prompts" / "system.md"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore", env_prefix="MILO_")
    google_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY")
    )
    model: str = "gemini-3.5-flash-lite"
    # Si el modelo principal está saturado (error 503), LangChain reintenta con este.
    fallback_model: str = "gemini-3.1-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = Field(default=3072, gt=0)
    # Aquí se guardan los artefactos generados: el índice de Chroma y la memoria de las conversaciones.
    storage_dir: Path = ROOT / "storage"

    @field_validator("storage_dir")
    @classmethod
    def relative_to_root(cls, path: Path) -> Path:
        return path if path.is_absolute() else ROOT / path

    def require_key(self) -> str:
        if not self.google_api_key or not self.google_api_key.get_secret_value().strip():
            raise RuntimeError(
                "Falta GOOGLE_API_KEY. Copia .env.example como .env y escribe tu clave de Gemini."
            )
        return self.google_api_key.get_secret_value()
