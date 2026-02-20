"""
Task Router
===========

Hybrid LLM routing: classifies features by type and complexity, then routes
to the optimal model tier based on cost preference.

The router is provider-agnostic - it returns a model TIER ("opus", "sonnet",
"haiku") which the orchestrator maps to an actual model name using the active
provider's model_tiers configuration.

Classification is rules-based (no LLM calls), keeping routing cost at zero.

Usage:
    from task_router import classify_task, route_task

    # Classify a feature
    task_type, complexity = classify_task(feature_dict)

    # Route to model tier
    model_tier = route_task(task_type, complexity, "balanced")

    # Or one-step:
    model_tier = route_feature(feature_dict, "balanced")
"""

from __future__ import annotations

import re
from typing import Literal

# ---------------------------------------------------------------------------
# Type definitions
# ---------------------------------------------------------------------------

TaskType = Literal["ui", "auth", "database", "api", "devops", "testing", "general"]
Complexity = Literal["simple", "medium", "complex"]
CostPreference = Literal["budget", "balanced", "quality"]
ModelTier = Literal["opus", "sonnet", "haiku"]

# ---------------------------------------------------------------------------
# Classification keywords
# ---------------------------------------------------------------------------

_TASK_TYPE_KEYWORDS: dict[TaskType, list[str]] = {
    "auth": [
        "auth", "login", "logout", "register", "signup", "sign-up", "sign up",
        "password", "reset password", "forgot password", "session", "jwt", "token",
        "oauth", "permission", "role", "rbac", "access control", "middleware",
        "protect", "guard", "credential", "2fa", "mfa", "verify email",
    ],
    "database": [
        "database", "migration", "schema", "model", "table", "column",
        "index", "query", "sql", "orm", "prisma", "drizzle", "sequelize",
        "seed", "fixture", "foreign key", "relation", "join",
    ],
    "ui": [
        "style", "css", "layout", "responsive", "mobile", "desktop",
        "color", "font", "spacing", "margin", "padding", "border",
        "animation", "transition", "hover", "focus", "theme", "dark mode",
        "light mode", "component", "button", "form", "input", "modal",
        "dialog", "dropdown", "menu", "nav", "sidebar", "header", "footer",
        "card", "grid", "flex", "display", "visual", "icon", "image",
        "page", "view", "render", "ui", "ux",
    ],
    "api": [
        "api", "endpoint", "route", "handler", "controller", "rest",
        "graphql", "trpc", "fetch", "request", "response", "status code",
        "middleware", "cors", "rate limit", "pagination", "filter", "sort",
        "search", "crud", "create", "read", "update", "delete",
        "webhook", "callback", "upload", "download",
    ],
    "devops": [
        "deploy", "ci", "cd", "pipeline", "docker", "container",
        "environment", "env", "config", "configuration", "setup",
        "install", "init", "scaffold", "build", "compile", "bundle",
        "webpack", "vite", "lint", "format", "prettier", "eslint",
        "test setup", "jest", "vitest", "playwright setup",
    ],
    "testing": [
        "test", "spec", "assert", "expect", "mock", "stub",
        "fixture", "e2e", "integration test", "unit test",
        "coverage", "regression",
    ],
}

# Words that indicate higher complexity
_COMPLEXITY_SIGNALS_COMPLEX: list[str] = [
    "security", "encrypt", "hash", "sanitize", "validate",
    "real-time", "realtime", "websocket", "sse", "streaming",
    "upload", "file", "image", "video", "audio",
    "payment", "stripe", "billing", "subscription",
    "notification", "email", "sms", "push",
    "search", "filter", "sort", "pagination",
    "analytics", "dashboard", "chart", "graph",
    "import", "export", "csv", "pdf",
    "multi-tenant", "workspace", "organization",
    "oauth", "sso", "2fa", "mfa",
    "migration", "schema change",
    "cache", "redis", "queue", "background job",
]

# Words that indicate lower complexity
_COMPLEXITY_SIGNALS_SIMPLE: list[str] = [
    "display", "show", "list", "render",
    "static", "text", "label", "title",
    "color", "font", "spacing", "margin", "padding",
    "link", "navigate", "redirect",
    "placeholder", "empty state", "loading",
    "toggle", "switch", "checkbox",
    "tooltip", "badge", "tag",
]


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_task(feature: dict) -> tuple[TaskType, Complexity]:
    """Classify a feature by task type and complexity.

    Uses keyword matching against feature name, description, and category.
    Returns (task_type, complexity).

    Args:
        feature: Feature dict with at least 'name', 'description', 'category'.
            May also include 'steps' (str or list) and 'depends_on' (list).

    Returns:
        Tuple of (task_type, complexity).
    """
    task_type = _classify_type(feature)
    complexity = _classify_complexity(feature, task_type)
    return task_type, complexity


def _classify_type(feature: dict) -> TaskType:
    """Determine the task type from feature metadata."""
    # Build searchable text from feature fields
    name = (feature.get("name") or "").lower()
    description = (feature.get("description") or "").lower()
    category = (feature.get("category") or "").lower()
    text = f"{name} {description} {category}"

    # Score each task type by keyword matches
    scores: dict[TaskType, int] = {}
    for task_type, keywords in _TASK_TYPE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text:
                # Name matches count double
                if kw in name:
                    score += 2
                else:
                    score += 1
        if score > 0:
            scores[task_type] = score

    if not scores:
        return "general"

    # Category hint: if feature category matches a type, boost it
    category_boost: dict[str, TaskType] = {
        "style": "ui",
        "styling": "ui",
        "functional": "general",
        "infrastructure": "devops",
        "security": "auth",
    }
    if category in category_boost and category_boost[category] in scores:
        scores[category_boost[category]] += 3

    # Auth always wins over API when both match (auth is a subset of API patterns)
    if "auth" in scores and "api" in scores and scores["auth"] >= scores["api"]:
        return "auth"

    return max(scores, key=lambda k: scores[k])


def _classify_complexity(feature: dict, task_type: TaskType) -> Complexity:
    """Determine complexity from feature metadata and task type."""
    name = (feature.get("name") or "").lower()
    description = (feature.get("description") or "").lower()
    text = f"{name} {description}"

    # Count complexity signals
    complex_hits = sum(1 for kw in _COMPLEXITY_SIGNALS_COMPLEX if kw in text)
    simple_hits = sum(1 for kw in _COMPLEXITY_SIGNALS_SIMPLE if kw in text)

    # Steps count: more steps = more complex
    steps = feature.get("steps")
    if isinstance(steps, list):
        step_count = len(steps)
    elif isinstance(steps, str):
        # Try to count steps from JSON-like string
        step_count = steps.count('"step"')
        if step_count == 0:
            step_count = len(steps) // 200  # rough heuristic
    else:
        step_count = 0

    # Dependencies: more deps = more complex (integration point)
    depends_on = feature.get("depends_on") or []
    if isinstance(depends_on, list):
        dep_count = len(depends_on)
    else:
        dep_count = 0

    # Auth and database tasks are inherently more complex
    type_complexity_bonus = {"auth": 1, "database": 1}.get(task_type, 0)

    # Compute complexity score
    score = (
        complex_hits * 2
        - simple_hits
        + (1 if step_count > 8 else 0)
        + (1 if step_count > 15 else 0)
        + (1 if dep_count > 3 else 0)
        + type_complexity_bonus
    )

    if score >= 3:
        return "complex"
    elif score >= 1:
        return "medium"
    else:
        return "simple"


# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------

# (task_type, complexity) -> {cost_preference: model_tier}
_ROUTING_TABLE: dict[tuple[TaskType, Complexity], dict[CostPreference, ModelTier]] = {
    # UI/styling
    ("ui", "simple"):  {"budget": "haiku", "balanced": "sonnet", "quality": "sonnet"},
    ("ui", "medium"):  {"budget": "sonnet", "balanced": "sonnet", "quality": "sonnet"},
    ("ui", "complex"): {"budget": "sonnet", "balanced": "sonnet", "quality": "opus"},
    # Auth/security - always at least sonnet
    ("auth", "simple"):  {"budget": "sonnet", "balanced": "sonnet", "quality": "opus"},
    ("auth", "medium"):  {"budget": "sonnet", "balanced": "opus", "quality": "opus"},
    ("auth", "complex"): {"budget": "sonnet", "balanced": "opus", "quality": "opus"},
    # Database/migration
    ("database", "simple"):  {"budget": "sonnet", "balanced": "sonnet", "quality": "opus"},
    ("database", "medium"):  {"budget": "sonnet", "balanced": "opus", "quality": "opus"},
    ("database", "complex"): {"budget": "opus", "balanced": "opus", "quality": "opus"},
    # API/backend
    ("api", "simple"):  {"budget": "haiku", "balanced": "sonnet", "quality": "sonnet"},
    ("api", "medium"):  {"budget": "sonnet", "balanced": "sonnet", "quality": "opus"},
    ("api", "complex"): {"budget": "sonnet", "balanced": "opus", "quality": "opus"},
    # DevOps/config
    ("devops", "simple"):  {"budget": "haiku", "balanced": "sonnet", "quality": "sonnet"},
    ("devops", "medium"):  {"budget": "haiku", "balanced": "sonnet", "quality": "sonnet"},
    ("devops", "complex"): {"budget": "sonnet", "balanced": "sonnet", "quality": "opus"},
    # Testing
    ("testing", "simple"):  {"budget": "haiku", "balanced": "sonnet", "quality": "sonnet"},
    ("testing", "medium"):  {"budget": "sonnet", "balanced": "sonnet", "quality": "sonnet"},
    ("testing", "complex"): {"budget": "sonnet", "balanced": "sonnet", "quality": "opus"},
    # General/unclassified
    ("general", "simple"):  {"budget": "haiku", "balanced": "sonnet", "quality": "sonnet"},
    ("general", "medium"):  {"budget": "sonnet", "balanced": "sonnet", "quality": "opus"},
    ("general", "complex"): {"budget": "sonnet", "balanced": "opus", "quality": "opus"},
}


def route_task(
    task_type: TaskType,
    complexity: Complexity,
    cost_preference: CostPreference = "balanced",
) -> ModelTier:
    """Route a classified task to a model tier.

    Args:
        task_type: The classified task type.
        complexity: The classified complexity level.
        cost_preference: Cost optimization preference.

    Returns:
        Model tier: "opus", "sonnet", or "haiku".
    """
    key = (task_type, complexity)
    preferences = _ROUTING_TABLE.get(key)
    if preferences is None:
        # Fallback: balanced defaults
        return "sonnet"
    return preferences.get(cost_preference, "sonnet")


def route_feature(
    feature: dict,
    cost_preference: CostPreference = "balanced",
) -> ModelTier:
    """One-step: classify and route a feature to a model tier.

    Args:
        feature: Feature dict with name, description, category, etc.
        cost_preference: Cost optimization preference.

    Returns:
        Model tier: "opus", "sonnet", or "haiku".
    """
    task_type, complexity = classify_task(feature)
    return route_task(task_type, complexity, cost_preference)


# ---------------------------------------------------------------------------
# Model tier resolution
# ---------------------------------------------------------------------------

# Default model tier mappings (used when provider doesn't specify model_tiers)
DEFAULT_MODEL_TIERS: dict[ModelTier, str] = {
    "opus": "claude-opus-4-5",
    "sonnet": "claude-sonnet-4-5",
    "haiku": "claude-haiku-4-5",
}


def resolve_model_tier(
    tier: ModelTier,
    provider_tiers: dict[str, str] | None = None,
) -> str:
    """Resolve a model tier to an actual model name.

    Uses provider-specific tier mappings if available, otherwise falls back
    to DEFAULT_MODEL_TIERS.

    Args:
        tier: Model tier ("opus", "sonnet", "haiku").
        provider_tiers: Optional provider-specific tier->model mapping
            from providers.json model_tiers section.

    Returns:
        Actual model name string.
    """
    if provider_tiers and tier in provider_tiers:
        return provider_tiers[tier]
    return DEFAULT_MODEL_TIERS.get(tier, DEFAULT_MODEL_TIERS["sonnet"])
