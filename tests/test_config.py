"""Tests for config module."""
import os
from unittest import mock
import pytest
from financy_talk.config import (
    get_api_key,
    get_model_config,
    DATA_DIR,
    OUTPUT_DIR,
    PROJECT_ROOT,
    ConfigError,
    SETTINGS_FILE,
    ModelConfig,
)


def test_get_api_key_from_env():
    with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test123"}):
        assert get_api_key() == "sk-test123"


def test_get_api_key_from_dotenv(tmp_path):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("DEEPSEEK_API_KEY=sk-dotenv456")
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("financy_talk.config.PROJECT_ROOT", tmp_path):
            result = get_api_key()
    assert result == "sk-dotenv456"


def test_get_api_key_missing(tmp_path):
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("financy_talk.config.PROJECT_ROOT", tmp_path):
            with pytest.raises(ConfigError):
                get_api_key()


def test_data_dir():
    assert DATA_DIR.name == "talkers"
    assert DATA_DIR == PROJECT_ROOT / "data" / "talkers"


def test_output_dir():
    assert OUTPUT_DIR.name == "output"
    assert OUTPUT_DIR == PROJECT_ROOT / "output"


class TestModelConfig:
    def test_defaults_when_settings_missing(self, tmp_path):
        """Fall back to built-in defaults when settings.yaml doesn't exist."""
        with mock.patch("financy_talk.config.SETTINGS_FILE", tmp_path / "nonexistent.yaml"):
            cfg = get_model_config("sonnet")
            assert cfg.model == "deepseek-chat"
            assert cfg.max_tokens == 4000

    def test_haiku_default(self, tmp_path):
        with mock.patch("financy_talk.config.SETTINGS_FILE", tmp_path / "nonexistent.yaml"):
            cfg = get_model_config("haiku")
            assert cfg.max_tokens == 2000

    def test_opus_default(self, tmp_path):
        with mock.patch("financy_talk.config.SETTINGS_FILE", tmp_path / "nonexistent.yaml"):
            cfg = get_model_config("opus")
            assert cfg.max_tokens == 8000

    def test_custom_settings(self, tmp_path):
        """Read model config from a real settings.yaml."""
        import yaml
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text(yaml.dump({
            "models": {
                "sonnet": {"model": "custom-model", "max_tokens": 1234},
            }
        }), encoding="utf-8")
        with mock.patch("financy_talk.config.SETTINGS_FILE", settings_file):
            cfg = get_model_config("sonnet")
            assert cfg.model == "custom-model"
            assert cfg.max_tokens == 1234

    def test_partial_custom_falls_back(self, tmp_path):
        """Missing fields fall back to defaults."""
        import yaml
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text(yaml.dump({
            "models": {
                "sonnet": {"model": "only-model"},
            }
        }), encoding="utf-8")
        with mock.patch("financy_talk.config.SETTINGS_FILE", settings_file):
            cfg = get_model_config("sonnet")
            assert cfg.model == "only-model"
            assert cfg.max_tokens == 4000  # default fallback
