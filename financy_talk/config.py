"""Configuration: API key loading and base paths."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "talkers"
OUTPUT_DIR = PROJECT_ROOT / "output"


class ConfigError(RuntimeError):
    """Configuration is invalid."""


def get_api_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ConfigError(
            f"OPENAI_API_KEY not set. Set it via environment or .env file at {PROJECT_ROOT / '.env'}"
        )
    return key
