"""Tests for config module."""

import pytest


class TestSettings:
    def test_validate_missing_username(self):
        from linkedin_mcp.config import Settings
        s = Settings(linkedin_password="pass")
        errors = s.validate()
        assert any("LINKEDIN_USERNAME" in e for e in errors)

    def test_validate_missing_password(self):
        from linkedin_mcp.config import Settings
        s = Settings(linkedin_username="user")
        errors = s.validate()
        assert any("LINKEDIN_PASSWORD" in e for e in errors)

    def test_validate_all_present(self):
        from linkedin_mcp.config import Settings
        s = Settings(linkedin_username="user", linkedin_password="pass")
        assert s.validate() == []

    def test_has_ai_true(self):
        from linkedin_mcp.config import Settings
        s = Settings(anthropic_api_key="sk-ant-xxx")
        assert s.has_ai is True

    def test_has_ai_false(self):
        from linkedin_mcp.config import Settings
        s = Settings()
        assert s.has_ai is False

    def test_repr_redacts_credentials(self):
        from linkedin_mcp.config import Settings
        s = Settings(linkedin_password="secret123", anthropic_api_key="sk-ant-xxx")
        r = repr(s)
        assert "secret123" not in r
        assert "sk-ant-xxx" not in r
        assert "***" in r

    def test_get_settings_from_env(self, monkeypatch):
        from linkedin_mcp.config import get_settings
        get_settings.cache_clear()
        monkeypatch.setenv("LINKEDIN_USERNAME", "testuser")
        monkeypatch.setenv("LINKEDIN_PASSWORD", "testpass")
        monkeypatch.setenv("CACHE_TTL_HOURS", "48")
        try:
            s = get_settings()
            assert s.linkedin_username == "testuser"
            assert s.cache_ttl_hours == 48
        finally:
            get_settings.cache_clear()

    def test_parse_int_fallback(self):
        from linkedin_mcp.config import _parse_int
        assert _parse_int("abc", 10) == 10
        assert _parse_int("42", 10) == 42
