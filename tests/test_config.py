"""
Tests for configuration module
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

# Add fastapi directory to path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "fastapi"))

from config import Settings


class TestSettingsDefaults:
    """Test default configuration values"""

    def test_default_values(self):
        """Test that defaults are set correctly"""
        with patch.dict(os.environ, {}, clear=True):
            # Override validators that require keys
            with patch.object(Settings, "validate_qdrant_key", lambda cls, v, info: v):
                with patch.object(Settings, "validate_openai_key", lambda cls, v, info: v):
                    settings = Settings()

                    assert settings.env == "staging"
                    assert settings.qdrant_host == "localhost"
                    assert settings.qdrant_port == 6333
                    assert settings.embed_provider == "openai"
                    assert settings.openai_embedding_model == "text-embedding-3-small"
                    assert settings.api_port == 8080
                    assert settings.log_level == "INFO"

    def test_environment_override(self):
        """Test that environment variables override defaults"""
        with patch.dict(
            os.environ,
            {
                "ENV": "production",
                "QDRANT_HOST": "qdrant.example.com",
                "QDRANT_PORT": "443",
                "QDRANT_API_KEY": "test-key",
                "OPENAI_API_KEY": "sk-test-key",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.env == "production"
            assert settings.qdrant_host == "qdrant.example.com"
            assert settings.qdrant_port == 443


class TestSettingsValidation:
    """Test configuration validation"""

    def test_production_requires_qdrant_key(self):
        """Test that production environment requires Qdrant API key"""
        with patch.dict(
            os.environ,
            {"ENV": "production", "OPENAI_API_KEY": "sk-test"},
            clear=True,
        ):
            with pytest.raises(ValidationError, match="QDRANT_API_KEY is required"):
                Settings()

    def test_openai_provider_requires_key(self):
        """Test that OpenAI provider requires API key"""
        with patch.dict(
            os.environ,
            {"EMBED_PROVIDER": "openai"},
            clear=True,
        ):
            with pytest.raises(ValidationError, match="OPENAI_API_KEY is required"):
                Settings()

    def test_invalid_port_rejected(self):
        """Test that invalid port numbers are rejected"""
        with patch.dict(
            os.environ,
            {
                "QDRANT_PORT": "70000",  # Invalid port
                "OPENAI_API_KEY": "sk-test",
            },
            clear=True,
        ):
            with pytest.raises(ValidationError):
                Settings()

    def test_invalid_env_rejected(self):
        """Test that invalid environment values are rejected"""
        with patch.dict(
            os.environ,
            {
                "ENV": "invalid",  # Not in Literal["staging", "production", "development"]
                "OPENAI_API_KEY": "sk-test",
            },
            clear=True,
        ):
            with pytest.raises(ValidationError):
                Settings()


class TestSettingsHelpers:
    """Test helper methods and properties"""

    def test_use_https_property(self):
        """Test that use_https returns True for port 443"""
        with patch.dict(
            os.environ,
            {"QDRANT_PORT": "443", "QDRANT_API_KEY": "test", "OPENAI_API_KEY": "sk-test"},
            clear=True,
        ):
            settings = Settings()
            assert settings.use_https is True

        with patch.dict(
            os.environ,
            {"QDRANT_PORT": "6333", "OPENAI_API_KEY": "sk-test"},
            clear=True,
        ):
            with patch.object(Settings, "validate_qdrant_key", lambda cls, v, info: v):
                settings = Settings()
                assert settings.use_https is False

    def test_is_production_property(self):
        """Test environment detection properties"""
        with patch.dict(
            os.environ,
            {
                "ENV": "production",
                "QDRANT_API_KEY": "test",
                "OPENAI_API_KEY": "sk-test",
            },
            clear=True,
        ):
            settings = Settings()
            assert settings.is_production is True
            assert settings.is_development is False

    def test_get_secret_methods(self):
        """Test that secret getters return plain text values"""
        with patch.dict(
            os.environ,
            {
                "QDRANT_API_KEY": "qdrant-secret",
                "OPENAI_API_KEY": "openai-secret",
            },
            clear=True,
        ):
            with patch.object(Settings, "validate_qdrant_key", lambda cls, v, info: v):
                settings = Settings()

                assert settings.get_qdrant_api_key() == "qdrant-secret"
                assert settings.get_openai_api_key() == "openai-secret"
