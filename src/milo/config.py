from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore", env_prefix="MILO_")
    google_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY")
    )
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = Field(default=3072, gt=0)
    model: str = "gemini-3.5-flash-lite"
    storage_dir: Path = ROOT / "storage"

    def require_key(self) -> str:
        if not self.google_api_key or not self.google_api_key.get_secret_value().strip():
            raise RuntimeError("Falta GOOGLE_API_KEY en el archivo .env de la raíz del proyecto.")
        return self.google_api_key.get_secret_value()
