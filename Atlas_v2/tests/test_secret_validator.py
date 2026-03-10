"""
Unit tests for SecretValidator.
"""

import unittest
from unittest.mock import patch, MagicMock
import os


# All known secret env var names — we override them to empty
ALL_SECRET_KEYS = [
    "GEMINI_API_KEY", "OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID", "PERPLEXITY_API_KEY", "GITHUB_PERSONAL_ACCESS_TOKEN",
]


def _make_env(**overrides):
    """Creates a mock getenv that returns empty for all secret keys by default."""
    secrets = {k: "" for k in ALL_SECRET_KEYS}
    secrets.update(overrides)

    def mock_getenv(key, default=""):
        return secrets.get(key, default)

    return mock_getenv


class TestSecretValidator(unittest.TestCase):
    """Tests for the Secret Validator module."""

    @patch("core.security.secret_validator.os.getenv")
    def test_validate_all_empty_env(self, mock_getenv):
        """All keys missing should report missing for required ones."""
        from core.security.secret_validator import SecretValidator

        mock_getenv.side_effect = _make_env()

        result = SecretValidator.validate_all(brain_type="gemini")
        self.assertIn("Gemini", result["missing"])
        self.assertEqual(result["malformed"], [])

    @patch("core.security.secret_validator.os.getenv")
    def test_validate_all_ollama_mode(self, mock_getenv):
        """In ollama mode, Gemini key should NOT be required."""
        from core.security.secret_validator import SecretValidator

        mock_getenv.side_effect = _make_env()

        result = SecretValidator.validate_all(brain_type="ollama")
        self.assertNotIn("Gemini", result["missing"])

    @patch("core.security.secret_validator.os.getenv")
    def test_valid_gemini_key(self, mock_getenv):
        """Valid Gemini key format should be recognized."""
        from core.security.secret_validator import SecretValidator

        fake_key = "AIzaSy" + "A" * 33
        mock_getenv.side_effect = _make_env(GEMINI_API_KEY=fake_key)

        result = SecretValidator.validate_all(brain_type="gemini")
        self.assertIn("Gemini", result["valid"])
        self.assertNotIn("Gemini", result["malformed"])

    @patch("core.security.secret_validator.os.getenv")
    def test_malformed_gemini_key(self, mock_getenv):
        """Gemini key with wrong format should be flagged."""
        from core.security.secret_validator import SecretValidator

        mock_getenv.side_effect = _make_env(GEMINI_API_KEY="bad_key_123")

        result = SecretValidator.validate_all(brain_type="gemini")
        self.assertIn("Gemini", result["malformed"])

    @patch("core.security.secret_validator.os.getenv")
    def test_valid_telegram_token(self, mock_getenv):
        """Valid Telegram bot token format."""
        from core.security.secret_validator import SecretValidator

        fake_token = "12345678:AAHdqTcvCH1vGW-" + "A" * 20
        mock_getenv.side_effect = _make_env(TELEGRAM_BOT_TOKEN=fake_token)

        result = SecretValidator.validate_all(brain_type="telegram")
        self.assertIn("Telegram Bot", result["valid"])

    @patch("core.security.secret_validator.os.getenv")
    def test_valid_openai_key(self, mock_getenv):
        """OpenAI key (optional) should not cause missing error."""
        from core.security.secret_validator import SecretValidator

        mock_getenv.side_effect = _make_env()

        result = SecretValidator.validate_all(brain_type="ollama")
        self.assertNotIn("OpenAI", result["missing"])

    def test_mask_value(self):
        """Mask should hide most of the value."""
        from core.security.secret_validator import SecretValidator

        masked = SecretValidator.mask_value("sk-proj-abc123xyz789")
        self.assertTrue(masked.endswith("789"))
        self.assertTrue(masked.startswith("*"))
        self.assertNotIn("abc123", masked)

    def test_mask_short_value(self):
        """Very short values should return ***."""
        from core.security.secret_validator import SecretValidator

        self.assertEqual(SecretValidator.mask_value("abc"), "***")
        self.assertEqual(SecretValidator.mask_value(""), "***")
        self.assertEqual(SecretValidator.mask_value(None), "***")

    @patch("builtins.print")
    @patch("core.security.secret_validator.os.getenv")
    def test_print_boot_report(self, mock_getenv, mock_print):
        """Boot report should print without errors."""
        from core.security.secret_validator import SecretValidator

        mock_getenv.side_effect = _make_env()

        result = SecretValidator.print_boot_report(brain_type="ollama")
        self.assertIsInstance(result, bool)
        mock_print.assert_called()

    @patch("core.security.secret_validator.os.getenv")
    def test_perplexity_key_format(self, mock_getenv):
        """Valid Perplexity key format."""
        from core.security.secret_validator import SecretValidator

        fake_key = "pplx-" + "a" * 40
        mock_getenv.side_effect = _make_env(PERPLEXITY_API_KEY=fake_key)

        result = SecretValidator.validate_all(brain_type="ollama")
        self.assertIn("Perplexity", result["valid"])

    @patch("core.security.secret_validator.os.getenv")
    def test_github_pat_format(self, mock_getenv):
        """Valid GitHub PAT format."""
        from core.security.secret_validator import SecretValidator

        fake_pat = "ghp_" + "A" * 36
        mock_getenv.side_effect = _make_env(GITHUB_PERSONAL_ACCESS_TOKEN=fake_pat)

        result = SecretValidator.validate_all(brain_type="ollama")
        self.assertIn("GitHub PAT", result["valid"])


if __name__ == "__main__":
    unittest.main()
