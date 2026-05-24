"""Configuration: API key loading and base paths."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data" / "talkers"
OUTPUT_DIR = PROJECT_ROOT / "output"


def get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("Error: OPENAI_API_KEY not set. Set it via environment or .env file.", file=sys.stderr)
        sys.exit(1)
    return key
