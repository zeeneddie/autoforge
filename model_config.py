"""
Per-Project Model Configuration
================================

Loads optional per-project model overrides from
``.mq-devengine/model_config.yaml``.

Priority chain (highest to lowest):
1. CLI flag (--model-*)
2. Project config (this module)  ← here
3. Global registry settings
4. DEFAULT_MODEL fallback

Usage::

    from model_config import get_project_models
    project_models = get_project_models(Path(project_dir))
    model = cli_flag or project_models.get("coding") or registry_setting or default
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_ALLOWED_ROLES = frozenset({"architect", "initializer", "coding", "testing"})


def get_project_models(project_dir: Path) -> dict[str, str]:
    """Load per-project model overrides from ``.mq-devengine/model_config.yaml``.

    Returns a dict with a subset of keys: ``architect``, ``initializer``,
    ``coding``, ``testing``.  Only keys that are explicitly set in the YAML
    file are present — absent keys mean "fall through to the next layer".

    Args:
        project_dir: Root directory of the project.

    Returns:
        Mapping of role name → model ID string.  Empty dict if no config file
        exists or the file is invalid.
    """
    path = project_dir / ".mq-devengine" / "model_config.yaml"
    if not path.exists():
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        logger.warning("Failed to read model_config.yaml for %s", project_dir, exc_info=True)
        return {}

    if not isinstance(data, dict):
        logger.warning("model_config.yaml for %s is not a YAML mapping — ignoring", project_dir)
        return {}

    if data.get("version") != 1:
        logger.warning(
            "model_config.yaml for %s has unsupported version %r — ignoring",
            project_dir,
            data.get("version"),
        )
        return {}

    models = data.get("models", {})
    if not isinstance(models, dict):
        logger.warning("model_config.yaml 'models' key for %s is not a mapping — ignoring", project_dir)
        return {}

    result: dict[str, str] = {}
    for role, model_id in models.items():
        if role not in _ALLOWED_ROLES:
            logger.debug("model_config.yaml: unknown role %r — skipping", role)
            continue
        if not isinstance(model_id, str) or not model_id.strip():
            logger.warning("model_config.yaml: model for role %r is not a non-empty string — skipping", role)
            continue
        result[role] = model_id.strip()

    return result
