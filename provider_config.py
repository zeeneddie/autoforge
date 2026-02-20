"""
Provider Configuration
======================

Manages provider profiles for switching between different API backends
(Claude subscription, Anthropic API, OpenRouter, Ollama).

Profiles are stored in ~/.mq-devengine/providers.json and include:
- Environment variable overrides per provider
- Per-agent-type model mappings (initializer, coding, testing)

Model selection priority: UI settings override > provider profile models > registry DEFAULT_MODEL
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from env_constants import API_ENV_VARS
from role_registry import get_agent_types

logger = logging.getLogger(__name__)

AGENT_TYPES = get_agent_types()

DEFAULT_PROVIDERS: dict[str, dict[str, Any]] = {
    "claude-sub": {
        "description": "Claude subscription (native CLI auth)",
        "env": {},
        "models": {
            "initializer": None,
            "coding": None,
            "testing": None,
        },
        "model_tiers": {
            "opus": "claude-opus-4-5",
            "sonnet": "claude-sonnet-4-5",
            "haiku": "claude-haiku-4-5",
        },
        "cost_tier": "subscription",
    },
    "claude-api": {
        "description": "Anthropic API (pay-per-use)",
        "env": {
            "ANTHROPIC_AUTH_TOKEN": "",
        },
        "models": {
            "initializer": None,
            "coding": None,
            "testing": None,
        },
        "model_tiers": {
            "opus": "claude-opus-4-5",
            "sonnet": "claude-sonnet-4-5",
            "haiku": "claude-haiku-4-5",
        },
        "cost_tier": "pay-per-token",
    },
    "openrouter": {
        "description": "OpenRouter (multi-vendor mix)",
        "env": {
            "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
            "ANTHROPIC_AUTH_TOKEN": "",
        },
        "models": {
            "initializer": "anthropic/claude-opus-4-5",
            "coding": "deepseek/deepseek-coder",
            "testing": "google/gemini-2.0-flash-exp",
        },
        "model_tiers": {
            "opus": "anthropic/claude-opus-4-5",
            "sonnet": "deepseek/deepseek-coder",
            "haiku": "google/gemini-2.0-flash-exp",
        },
        "cost_tier": "pay-per-token",
    },
    "ollama": {
        "description": "Ollama lokaal (DeepSeek)",
        "env": {
            "ANTHROPIC_BASE_URL": "http://192.168.27.17:11434",
            "ANTHROPIC_AUTH_TOKEN": "ollama",
            "API_TIMEOUT_MS": "3000000",
        },
        "models": {
            "initializer": "deepseek-coder-v2:16B",
            "coding": "deepseek-coder-v2:16B",
            "testing": "deepseek-coder-v2:16B",
        },
        "model_tiers": {
            "opus": "deepseek-coder-v2:16B",
            "sonnet": "deepseek-coder-v2:16B",
            "haiku": "deepseek-coder-v2:16B",
        },
        "cost_tier": "pay-per-token",
    },
}


def _get_providers_path() -> Path:
    """Get path to providers.json in the config directory."""
    config_dir = Path.home() / ".mq-devengine"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "providers.json"


def load_providers() -> dict[str, dict[str, Any]]:
    """Load provider profiles from ~/.mq-devengine/providers.json.

    Scaffolds default profiles if the file doesn't exist.

    Returns:
        Dictionary of provider profiles keyed by name.
    """
    path = _get_providers_path()
    if not path.exists():
        # Scaffold defaults
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PROVIDERS, f, indent=2)
        logger.info("Created default providers.json at %s", path)
        return dict(DEFAULT_PROVIDERS)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("providers.json is not a dict, using defaults")
            return dict(DEFAULT_PROVIDERS)
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load providers.json: %s", e)
        return dict(DEFAULT_PROVIDERS)


def save_providers(providers: dict[str, dict[str, Any]]) -> None:
    """Save provider profiles to ~/.mq-devengine/providers.json."""
    path = _get_providers_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(providers, f, indent=2)


def get_active_provider() -> str | None:
    """Get the currently active provider name from registry settings.

    Returns:
        Provider name (e.g. 'openrouter') or None for legacy mode.
    """
    from registry import get_setting
    value = get_setting("active_provider")
    if not value or value == "none":
        return None
    return value


def set_active_provider(name: str | None) -> None:
    """Set the active provider in registry settings.

    Args:
        name: Provider name or None to clear (legacy mode).
    """
    from registry import set_setting, delete_setting
    if name is None:
        delete_setting("active_provider")
    else:
        providers = load_providers()
        if name not in providers:
            raise ValueError(f"Unknown provider: {name}")
        set_setting("active_provider", name)
    logger.info("Active provider set to: %s", name or "(legacy)")


def get_provider_env() -> dict[str, str]:
    """Get environment variable overrides for the active provider.

    When a provider is active, returns ONLY the env vars from that profile
    (not from os.environ / .env). When no provider is active, falls back
    to the legacy behavior of reading API_ENV_VARS from os.environ.

    Returns:
        Dict of environment variable name -> value.
    """
    active = get_active_provider()
    if active is None:
        # Legacy mode: read from os.environ
        env = {}
        for var in API_ENV_VARS:
            value = os.getenv(var)
            if value:
                env[var] = value
        return env

    providers = load_providers()
    profile = providers.get(active)
    if not profile:
        logger.warning("Active provider '%s' not found in providers.json", active)
        return {}

    # Return only non-empty env vars from the profile
    return {k: v for k, v in profile.get("env", {}).items() if v}


def get_provider_models() -> dict[str, str | None]:
    """Get per-agent-type model mappings for the active provider.

    Returns:
        Dict like {"initializer": "model-id", "coding": ..., "testing": ...}
        Values are None when the provider doesn't specify a model for that type.
    """
    active = get_active_provider()
    if active is None:
        return {"initializer": None, "coding": None, "testing": None}

    providers = load_providers()
    profile = providers.get(active)
    if not profile:
        return {"initializer": None, "coding": None, "testing": None}

    models = profile.get("models", {})
    return {
        "initializer": models.get("initializer") or None,
        "coding": models.get("coding") or None,
        "testing": models.get("testing") or None,
    }


def get_provider_model_tiers() -> dict[str, str] | None:
    """Get model tier mappings for the active provider.

    Used by the task router to resolve model tiers (opus/sonnet/haiku)
    to actual model names for the active provider.

    Returns:
        Dict like {"opus": "model-id", "sonnet": "model-id", "haiku": "model-id"}
        or None if no provider is active or no model_tiers configured.
    """
    active = get_active_provider()
    if active is None:
        return None

    providers = load_providers()
    profile = providers.get(active)
    if not profile:
        return None

    tiers = profile.get("model_tiers")
    if not tiers or not isinstance(tiers, dict):
        return None

    return tiers


def get_provider_info(name: str) -> dict[str, Any] | None:
    """Get info about a specific provider profile.

    Returns:
        Provider profile dict or None if not found.
    """
    providers = load_providers()
    return providers.get(name)


def has_credentials(profile: dict[str, Any]) -> bool:
    """Check if a provider profile has non-empty credentials configured.

    A profile has credentials if it either has no env vars that need values
    (e.g. claude-sub) or all token/auth vars have non-empty values.
    """
    env = profile.get("env", {})
    if not env:
        return True  # No credentials needed (e.g. claude-sub)

    # Check if auth-related vars have values
    auth_keys = [k for k in env if "TOKEN" in k or "KEY" in k or "SECRET" in k]
    if not auth_keys:
        return True  # No auth vars to check

    return all(bool(env.get(k)) for k in auth_keys)


def mask_credentials(env: dict[str, str]) -> dict[str, str]:
    """Mask sensitive values in env dict for safe display.

    Returns:
        New dict with token/key values masked.
    """
    masked = {}
    for k, v in env.items():
        if ("TOKEN" in k or "KEY" in k or "SECRET" in k) and v:
            masked[k] = v[:8] + "..." if len(v) > 8 else "***"
        else:
            masked[k] = v
    return masked
