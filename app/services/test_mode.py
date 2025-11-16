"""
Test Mode configuration and helpers.

Enables safe, deterministic behavior for integration testing without relying on
external services or production data sources.
"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TestMode:
    """
    Centralized access to Test Mode configuration.
    """
    ENV_FLAG = "TEST_MODE"

    @classmethod
    def is_enabled(cls) -> bool:
        return os.getenv(cls.ENV_FLAG, "false").lower() == "true"

    @classmethod
    def describe(cls) -> Dict[str, Any]:
        enabled = cls.is_enabled()
        return {
            "enabled": enabled,
            "behaviors": {
                "llm_engine_mock": True if enabled else False,
                "external_api_calls_disabled": True if enabled else False,
                "safe_audit_logging": True,  # writes to configured local file
                "deterministic_mocks": True,
            },
            "env": {
                "TEST_MODE": os.getenv(cls.ENV_FLAG, "false"),
                "GEMINI_API_KEY_set": bool(os.getenv("GEMINI_API_KEY")),
                "AUDIT_LOG_FILE": os.getenv("AUDIT_LOG_FILE", "audit.log"),
            },
        }


