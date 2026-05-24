"""Configuration: API key loading, base paths, and model settings."""
import os
from pathlib import Path
from dataclasses import dataclass

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "talkers"
OUTPUT_DIR = PROJECT_ROOT / "output"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
SETTINGS_FILE = PROJECT_ROOT / "settings.yaml"

# Default model tiers — overridden by settings.yaml if present
_DEFAULT_SETTINGS = {
    "models": {
        "haiku":  {"model": "deepseek-chat", "max_tokens": 2000},
        "sonnet": {"model": "deepseek-chat", "max_tokens": 4000},
        "opus":   {"model": "deepseek-chat", "max_tokens": 8000},
    }
}


@dataclass(frozen=True)
class ModelConfig:
    model: str
    max_tokens: int


class ConfigError(RuntimeError):
    """Configuration is invalid."""


def _load_settings() -> dict:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_model_config(tier: str) -> ModelConfig:
    """Return model config for a given tier (haiku/sonnet/opus).

    Falls back to defaults if settings.yaml is missing or incomplete.
    """
    settings = _load_settings()
    models = settings.get("models", {})
    tier_config = models.get(tier, _DEFAULT_SETTINGS["models"].get(tier, {}))
    return ModelConfig(
        model=tier_config.get("model", "deepseek-chat"),
        max_tokens=tier_config.get("max_tokens", 4000),
    )


def get_api_key() -> str:
    # Priority: env var > .env file > settings.yaml
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        return key

    settings = _load_settings()
    key = settings.get("api_key", "")
    if key:
        return key

    raise ConfigError(
        f"DEEPSEEK_API_KEY not set. Options:\n"
        f"  1. export DEEPSEEK_API_KEY=sk-xxxxx\n"
        f"  2. echo 'DEEPSEEK_API_KEY=sk-xxxxx' > {PROJECT_ROOT / '.env'}\n"
        f"  3. Set 'api_key' field in {SETTINGS_FILE}"
    )
