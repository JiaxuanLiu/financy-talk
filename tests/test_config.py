"""Tests for config module."""
import os
from unittest import mock
from financy_talk.config import get_api_key, DATA_DIR, OUTPUT_DIR, PROJECT_ROOT


def test_get_api_key_from_env():
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
        assert get_api_key() == "sk-test123"


def test_get_api_key_from_dotenv(tmp_path):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("OPENAI_API_KEY=sk-dotenv456")
    with mock.patch.dict(os.environ, {}, clear=True):
        from dotenv import load_dotenv
        load_dotenv(tmp_path / ".env")
        result = get_api_key()
    assert result == "sk-dotenv456"


def test_get_api_key_missing(tmp_path):
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("financy_talk.config.PROJECT_ROOT", tmp_path):
            try:
                get_api_key()
                assert False, "Should have raised"
            except SystemExit:
                pass


def test_data_dir():
    assert DATA_DIR.name == "talkers"
    assert DATA_DIR == PROJECT_ROOT / "data" / "talkers"
    assert DATA_DIR.exists()


def test_output_dir():
    assert OUTPUT_DIR.name == "output"
    assert OUTPUT_DIR == PROJECT_ROOT / "output"
    assert OUTPUT_DIR.exists()
