"""
Unit tests for configuration module
"""

import pytest
from unittest.mock import patch
from src.core.config import Settings, get_settings


class TestSettings:
    """Test Settings class"""

    def test_settings_defaults(self):
        """Test default settings values"""
        settings = Settings(
            DATABASE_URL="sqlite:///:memory:",
            GLM_API_KEY="test_key",
            SECRET_KEY="test_secret"
        )

        assert settings.APP_NAME == "AI Agent Prompt Generator"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.DEBUG == False
        assert settings.ENVIRONMENT == "production"
        assert settings.GLM_MODEL == "glm-4"
        assert settings.GLM_TIMEOUT == 30
        assert settings.MAX_CONCURRENT_SESSIONS == 100

    def test_settings_validation_required_fields(self):
        """Test that required fields raise validation errors"""
        with pytest.raises(Exception):
            Settings()  # Missing required fields

    def test_settings_from_env(self, monkeypatch):
        """Test loading settings from environment variables"""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.setenv("GLM_API_KEY", "env_test_key")
        monkeypatch.setenv("SECRET_KEY", "env_test_secret")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("APP_NAME", "Custom App Name")

        settings = Settings()

        assert settings.GLM_API_KEY == "env_test_key"
        assert settings.SECRET_KEY == "env_test_secret"
        assert settings.DEBUG == True
        assert settings.APP_NAME == "Custom App Name"

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance"""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    @patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "sqlite:///:memory:",
            "GLM_API_KEY": "test_key",
            "SECRET_KEY": "test_secret"
        }
    )
    def test_get_settings_with_env(self):
        """Test get_settings with environment variables"""
        settings = get_settings()

        assert settings.DATABASE_URL == "sqlite:///:memory:"
        assert settings.GLM_API_KEY == "test_key"
        assert settings.SECRET_KEY == "test_secret"


@pytest.mark.unit
class TestSettingsIntegration:
    """Integration tests for settings"""

    def test_full_configuration(self):
        """Test full configuration with all parameters"""
        settings = Settings(
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost/test",
            GLM_API_KEY="test_glm_key",
            SECRET_KEY="test_secret_key",
            APP_NAME="Test App",
            DEBUG=True,
            LOG_LEVEL="debug",
            MAX_CONCURRENT_SESSIONS=200,
            GLM_TIMEOUT=60
        )

        assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/test"
        assert settings.GLM_API_KEY == "test_glm_key"
        assert settings.SECRET_KEY == "test_secret_key"
        assert settings.APP_NAME == "Test App"
        assert settings.DEBUG == True
        assert settings.LOG_LEVEL == "debug"
        assert settings.MAX_CONCURRENT_SESSIONS == 200
        assert settings.GLM_TIMEOUT == 60

    def test_cors_configuration(self):
        """Test CORS configuration"""
        settings = Settings(
            DATABASE_URL="sqlite:///:memory:",
            GLM_API_KEY="test_key",
            SECRET_KEY="test_secret",
            ALLOWED_ORIGINS=["http://localhost:3000", "https://example.com"]
        )

        assert len(settings.ALLOWED_ORIGINS) == 2
        assert "http://localhost:3000" in settings.ALLOWED_ORIGINS
        assert "https://example.com" in settings.ALLOWED_ORIGINS

    def test_rate_limiting_configuration(self):
        """Test rate limiting configuration"""
        settings = Settings(
            DATABASE_URL="sqlite:///:memory:",
            GLM_API_KEY="test_key",
            SECRET_KEY="test_secret",
            RATE_LIMIT_REQUESTS=150,
            RATE_LIMIT_WINDOW=1800
        )

        assert settings.RATE_LIMIT_REQUESTS == 150
        assert settings.RATE_LIMIT_WINDOW == 1800