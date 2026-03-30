from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    project_root = Path(__file__).resolve().parents[3]
    api_root = Path(__file__).resolve().parents[2]
    for env_file in (project_root / ".env", api_root / ".env"):
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)


_load_env_files()


@dataclass(frozen=True)
class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Desafio API")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    # Defaults orientados para execucao em Docker Compose.
    PG_HOST: str = os.getenv("PG_HOST", "postgres")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
    PG_DATABASE: str = os.getenv("PG_DATABASE", "sncr")
    PG_USER: str = os.getenv("PG_USER", "postgres")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD", "postgres")


settings = Settings()
