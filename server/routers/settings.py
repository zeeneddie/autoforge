"""
Settings Router
===============

API endpoints for global settings management.
Settings are stored in the registry database and shared across all projects.
"""

import mimetypes
import sys

from fastapi import APIRouter

from ..schemas import (
    ModelInfo,
    ModelsResponse,
    ProviderProfile,
    ProvidersListResponse,
    SettingsResponse,
    SettingsUpdate,
)
from ..services.chat_constants import ROOT_DIR

# Mimetype fix for Windows - must run before StaticFiles is mounted
mimetypes.add_type("text/javascript", ".js", True)

# Ensure root is on sys.path for registry import
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from registry import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    get_all_settings,
    set_setting,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _parse_yolo_mode(value: str | None) -> bool:
    """Parse YOLO mode string to boolean."""
    return (value or "false").lower() == "true"


def _detect_mode() -> tuple[bool, bool]:
    """Detect GLM and Ollama mode from the active provider env.

    Uses provider_config.get_provider_env() so mode detection reflects
    the active provider profile rather than raw os.environ.
    """
    from provider_config import get_provider_env
    env = get_provider_env()
    base_url = env.get("ANTHROPIC_BASE_URL", "")
    is_ollama = ":11434" in base_url
    is_glm = bool(base_url) and not is_ollama
    return is_glm, is_ollama


@router.get("/models", response_model=ModelsResponse)
async def get_available_models():
    """Get list of available models.

    Frontend should call this to get the current list of models
    instead of hardcoding them.
    """
    return ModelsResponse(
        models=[ModelInfo(id=m["id"], name=m["name"]) for m in AVAILABLE_MODELS],
        default=DEFAULT_MODEL,
    )


def _parse_int(value: str | None, default: int) -> int:
    """Parse integer setting with default fallback."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_bool(value: str | None, default: bool = False) -> bool:
    """Parse boolean setting with default fallback."""
    if value is None:
        return default
    return value.lower() == "true"


def _build_settings_response(all_settings: dict[str, str]) -> SettingsResponse:
    """Build a SettingsResponse from registry settings dict."""
    from provider_config import get_active_provider
    glm_mode, ollama_mode = _detect_mode()
    return SettingsResponse(
        yolo_mode=_parse_yolo_mode(all_settings.get("yolo_mode")),
        model=all_settings.get("model", DEFAULT_MODEL),
        model_initializer=all_settings.get("model_initializer") or None,
        model_coding=all_settings.get("model_coding") or None,
        model_testing=all_settings.get("model_testing") or None,
        glm_mode=glm_mode,
        ollama_mode=ollama_mode,
        active_provider=get_active_provider(),
        testing_agent_ratio=_parse_int(all_settings.get("testing_agent_ratio"), 1),
        playwright_headless=_parse_bool(all_settings.get("playwright_headless"), default=True),
        batch_size=_parse_int(all_settings.get("batch_size"), 3),
        review_enabled=_parse_bool(all_settings.get("review_enabled"), default=False),
        architect_enabled=_parse_bool(all_settings.get("architect_enabled"), default=False),
        routing_enabled=_parse_bool(all_settings.get("routing_enabled"), default=False),
        cost_preference=all_settings.get("cost_preference", "balanced"),
    )


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Get current global settings."""
    return _build_settings_response(get_all_settings())


@router.patch("", response_model=SettingsResponse)
async def update_settings(update: SettingsUpdate):
    """Update global settings."""
    if update.yolo_mode is not None:
        set_setting("yolo_mode", "true" if update.yolo_mode else "false")

    if update.model is not None:
        set_setting("model", update.model)

    if update.model_initializer is not None:
        set_setting("model_initializer", update.model_initializer)
    if update.model_coding is not None:
        set_setting("model_coding", update.model_coding)
    if update.model_testing is not None:
        set_setting("model_testing", update.model_testing)

    if update.active_provider is not None:
        from provider_config import set_active_provider
        provider = update.active_provider if update.active_provider != "none" else None
        set_active_provider(provider)

    if update.testing_agent_ratio is not None:
        set_setting("testing_agent_ratio", str(update.testing_agent_ratio))

    if update.playwright_headless is not None:
        set_setting("playwright_headless", "true" if update.playwright_headless else "false")

    if update.batch_size is not None:
        set_setting("batch_size", str(update.batch_size))

    if update.review_enabled is not None:
        set_setting("review_enabled", "true" if update.review_enabled else "false")

    if update.architect_enabled is not None:
        set_setting("architect_enabled", "true" if update.architect_enabled else "false")

    if update.routing_enabled is not None:
        set_setting("routing_enabled", "true" if update.routing_enabled else "false")

    if update.cost_preference is not None:
        set_setting("cost_preference", update.cost_preference)

    return _build_settings_response(get_all_settings())


@router.get("/providers", response_model=ProvidersListResponse)
async def get_providers():
    """Get all provider profiles with masked credentials."""
    from provider_config import (
        get_active_provider,
        has_credentials,
        load_providers,
        mask_credentials,
    )

    active = get_active_provider()
    providers = load_providers()

    profiles = []
    for name, profile in providers.items():
        profiles.append(ProviderProfile(
            name=name,
            description=profile.get("description", ""),
            active=(name == active),
            has_credentials=has_credentials(profile),
            models=profile.get("models", {}),
            env_masked=mask_credentials(profile.get("env", {})),
        ))

    return ProvidersListResponse(providers=profiles, active=active)
