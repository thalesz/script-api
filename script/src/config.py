import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv


def _load_env_files() -> None:
	project_root = Path(__file__).resolve().parents[2]
	script_root = Path(__file__).resolve().parents[1]
	for env_file in (project_root / ".env", script_root / ".env"):
		if env_file.exists():
			load_dotenv(dotenv_path=env_file, override=False)


def _to_bool(value: str | None, default: bool) -> bool:
	if value is None:
		return default
	return str(value).strip().lower() in ("1", "true", "yes", "on")


def _to_int(value: str | None, default: int) -> int:
	try:
		return int(str(value).strip()) if value is not None else default
	except (TypeError, ValueError):
		return default


def _to_float(value: str | None, default: float) -> float:
	try:
		return float(str(value).strip()) if value is not None else default
	except (TypeError, ValueError):
		return default


_load_env_files()


@dataclass
class Config:
	BASE_DIR: Path = Path(__file__).resolve().parents[1]

	DATA_DIR: Path = BASE_DIR / "data"
	RAW_DIR: Path = DATA_DIR / "raw"
	PROCESSED_DIR: Path = DATA_DIR / "processed"
	CHECKPOINT_DIR: Path = DATA_DIR / "checkpoints"
	LOGS_DIR: Path = BASE_DIR / "logs"
	OUTPUT_DIR: Path = BASE_DIR / "output"

	TARGET_UFS: List[str] = ("AM", "PA", "RO")
	BASE_URL: str = os.getenv("BASE_URL", "https://data-engineer-challenge-production.up.railway.app/")

	# Runtime configuration (override as needed)
	HEADLESS: bool = _to_bool(os.getenv("HEADLESS"), False)
	# Directory where CSVs and screenshots will be saved (Path)
	DOWNLOAD_DIR: Path = OUTPUT_DIR
	# Retry and timeout settings
	MAX_ATTEMPTS: int = _to_int(os.getenv("MAX_ATTEMPTS"), 100)
	# timeouts in milliseconds or seconds as noted
	DOWNLOAD_TIMEOUT: int = _to_int(os.getenv("DOWNLOAD_TIMEOUT"), 15000)  # ms for expect_download
	CAPTCHA_TIMEOUT: int = _to_int(os.getenv("CAPTCHA_TIMEOUT"), 7)  # seconds to wait for captcha element
	SHORT_SLEEP: float = _to_float(os.getenv("SHORT_SLEEP"), 0.8)  # seconds pause between quick retries
	SELECT_TIMEOUT: int = _to_int(os.getenv("SELECT_TIMEOUT"), 5)  # seconds for select changes
	# When True, any existing checkpoint will be removed at script start and processing
	# will start from zero. Set to False to resume from existing checkpoint.json.
	RESET_CHECKPOINT: bool = _to_bool(os.getenv("RESET_CHECKPOINT"), True)
	# Concurrency: number of parallel browser workers (1 = no parallelism)
	CONCURRENCY: int = _to_int(os.getenv("CONCURRENCY"), 3)
	# Additional full rounds to retry states that failed in a previous round.
	STATE_RETRY_ROUNDS: int = _to_int(os.getenv("STATE_RETRY_ROUNDS"), 2)


# Module-level instance for easy import
cfg = Config()

# Backwards-compatible module-level names
BASE_DIR = cfg.BASE_DIR
DATA_DIR = cfg.DATA_DIR
RAW_DIR = cfg.RAW_DIR
PROCESSED_DIR = cfg.PROCESSED_DIR
CHECKPOINT_DIR = cfg.CHECKPOINT_DIR
LOGS_DIR = cfg.LOGS_DIR
OUTPUT_DIR = cfg.OUTPUT_DIR

TARGET_UFS = cfg.TARGET_UFS
BASE_URL = cfg.BASE_URL

HEADLESS = cfg.HEADLESS
DOWNLOAD_DIR = cfg.DOWNLOAD_DIR
MAX_ATTEMPTS = cfg.MAX_ATTEMPTS
DOWNLOAD_TIMEOUT = cfg.DOWNLOAD_TIMEOUT
CAPTCHA_TIMEOUT = cfg.CAPTCHA_TIMEOUT
SHORT_SLEEP = cfg.SHORT_SLEEP
SELECT_TIMEOUT = cfg.SELECT_TIMEOUT
RESET_CHECKPOINT = cfg.RESET_CHECKPOINT
CONCURRENCY = cfg.CONCURRENCY
STATE_RETRY_ROUNDS = cfg.STATE_RETRY_ROUNDS