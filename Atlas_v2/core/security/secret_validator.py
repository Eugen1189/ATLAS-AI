"""
AXIS Secret Validator — Validates API key presence and format on boot.
Never logs or prints actual key values, only status.
"""

import os
import re
from core.logger import logger


class SecretValidator:
    """
    Validates that required secrets are present and correctly formatted.
    Used during AXIS boot to provide early warnings instead of mid-session crashes.
    """

    # Key name → (env var, regex pattern for format, required flag)
    KEY_DEFINITIONS = {
        "Gemini": {
            "env": "GEMINI_API_KEY",
            "pattern": r"^AIzaSy[A-Za-z0-9_-]{33}$",
            "required_for": "gemini",
        },
        "OpenAI": {
            "env": "OPENAI_API_KEY",
            "pattern": r"^sk-(proj-)?[A-Za-z0-9-_]{20,}$",
            "required_for": None,  # Optional
        },
        "Telegram Bot": {
            "env": "TELEGRAM_BOT_TOKEN",
            "pattern": r"^\d{8,}:[A-Za-z0-9_-]{35,}$",
            "required_for": "telegram",
        },
        "Telegram Chat ID": {
            "env": "TELEGRAM_CHAT_ID",
            "pattern": r"^\d{5,}$",
            "required_for": "telegram",
        },
        "Perplexity": {
            "env": "PERPLEXITY_API_KEY",
            "pattern": r"^pplx-[A-Za-z0-9]{20,}$",
            "required_for": None,  # Optional
        },
        "GitHub PAT": {
            "env": "GITHUB_PERSONAL_ACCESS_TOKEN",
            "pattern": r"^gh[ps]_[A-Za-z0-9]{36,}$",
            "required_for": None,  # Optional
        },
        "Context7": {
            "env": "CONTEXT7_API_KEY",
            "pattern": r"^[A-Za-z0-9_-]{20,}$",
            "required_for": None,  # Optional for now, but used by MCP Hub
        },
    }

    @classmethod
    def validate_all(cls, brain_type: str = "ollama") -> dict:
        """
        Validates all known API keys.

        Args:
            brain_type: Current AI_BRAIN setting ('gemini' or 'ollama')

        Returns:
            dict with keys: valid (list), missing (list), malformed (list), warnings (list)
        """
        result = {
            "valid": [],
            "missing": [],
            "malformed": [],
            "warnings": [],
        }

        for name, config in cls.KEY_DEFINITIONS.items():
            env_var = config["env"]
            pattern = config["pattern"]
            required_for = config["required_for"]

            value = os.getenv(env_var, "").strip()

            if not value:
                if required_for == brain_type:
                    result["missing"].append(name)
                    logger.warning("secrets.missing_required",
                                   key_name=name,
                                   env_var=env_var)
                elif required_for is not None:
                    # Required for a different brain type — just note it
                    pass
                else:
                    # Optional key not set — that's fine
                    result["warnings"].append(
                        f"{name} ({env_var}) not set - feature disabled"
                    )

                continue

            # Validate format (without logging the actual value)
            if pattern and not re.match(pattern, value):
                result["malformed"].append(name)
                # Show only the first 8 chars for debugging, mask the rest
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                logger.warning("secrets.malformed_key",
                               key_name=name,
                               preview=masked)
            else:
                result["valid"].append(name)

        return result

    @classmethod
    def print_boot_report(cls, brain_type: str = "ollama"):
        """
        Prints a formatted security status report during AXIS boot.
        """
        result = cls.validate_all(brain_type)

        print("\n[SECRET VALIDATOR REPORT]")

        if result["valid"]:
            for name in result["valid"]:
                print(f"  [OK] {name}: configured")

        if result["warnings"]:
            for warning in result["warnings"]:
                print(f"  [WARN] {warning}")

        if result["malformed"]:
            for name in result["malformed"]:
                print(f"  [ERROR] {name}: MALFORMED (check format)")

        if result["missing"]:
            for name in result["missing"]:
                print(f"  [CRITICAL] {name}: MISSING (required for {brain_type})")

        has_issues = bool(result["missing"] or result["malformed"])

        if not has_issues:
            print("  [STATUS] All required secrets OK")
        else:
            print("  [STATUS] Fix issues above before proceeding")

        print("-" * 40 + "\n")

        return not has_issues

    @classmethod
    def mask_value(cls, value: str, visible_chars: int = 4) -> str:
        """
        Masks a secret value for safe logging.
        Shows only the last N characters.

        Example: "sk-proj-abc123xyz" -> "***********xyz"
        """
        if not value or len(value) <= visible_chars:
            return "***"
        return "*" * (len(value) - visible_chars) + value[-visible_chars:]
