"""
Agent Role Registry
===================

Data-driven agent role definitions for BMAD-upgradable architecture.

Each role defines:
- template: Prompt template name (loaded by prompts.load_prompt)
- tools: MCP feature tools exposed to this agent type
- max_turns: Maximum conversation turns
- model_tier: Model tier key (maps to provider_config model slots)
- phase: Execution order in workflow (lower = earlier)

Adding a new agent role:
1. Add an entry to AGENT_ROLES below
2. Drop a prompt template in .claude/templates/{template}.template.md
No code changes in client.py, agent.py, etc. needed.

Overridable per project via .mq-devengine/roles.json (future).
"""

from typing import Any

# ---------------------------------------------------------------------------
# MCP tool lists per agent role
# Only expose the tools each agent type actually needs, reducing tool schema
# overhead and preventing agents from calling tools meant for other roles.
# ---------------------------------------------------------------------------

_INITIALIZER_TOOLS = [
    "mcp__features__feature_get_stats",
    "mcp__features__feature_create_bulk",
    "mcp__features__feature_create",
    "mcp__features__feature_add_dependency",
    "mcp__features__feature_set_dependencies",
    # Session memory tools (Sprint 7.4)
    "mcp__features__memory_store",
    "mcp__features__memory_recall",
]

_CODING_TOOLS = [
    "mcp__features__feature_get_stats",
    "mcp__features__feature_get_by_id",
    "mcp__features__feature_get_summary",
    "mcp__features__feature_claim_and_get",
    "mcp__features__feature_mark_in_progress",
    "mcp__features__feature_mark_passing",
    "mcp__features__feature_mark_failing",
    "mcp__features__feature_mark_for_review",
    "mcp__features__feature_skip",
    "mcp__features__feature_clear_in_progress",
    # Session memory tools (Sprint 7.4)
    "mcp__features__memory_store",
    "mcp__features__memory_recall",
    "mcp__features__memory_recall_for_feature",
]

_TESTING_TOOLS = [
    "mcp__features__feature_get_stats",
    "mcp__features__feature_get_by_id",
    "mcp__features__feature_get_summary",
    "mcp__features__feature_mark_passing",
    "mcp__features__feature_mark_failing",
]

_ARCHITECT_TOOLS = [
    # Session memory tools - architect stores architecture decisions + spec constraints
    "mcp__features__memory_store",
    "mcp__features__memory_recall",
]

_REVIEWER_TOOLS = [
    "mcp__features__feature_get_stats",
    "mcp__features__feature_get_by_id",
    "mcp__features__feature_get_summary",
    "mcp__features__feature_approve",
    "mcp__features__feature_reject",
    # Session memory tools (Sprint 7.4)
    "mcp__features__memory_recall",
    "mcp__features__memory_recall_for_feature",
]

# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

AGENT_ROLES: dict[str, dict[str, Any]] = {
    "architect": {
        "template": "architect_prompt",
        "tools": _ARCHITECT_TOOLS,
        "max_turns": 200,
        "model_tier": "initializer",
        "phase": 0,
    },
    "initializer": {
        "template": "initializer_prompt",
        "tools": _INITIALIZER_TOOLS,
        "max_turns": 300,
        "model_tier": "initializer",
        "phase": 1,
    },
    "coding": {
        "template": "coding_prompt",
        "tools": _CODING_TOOLS,
        "max_turns": 300,
        "model_tier": "coding",
        "phase": 2,
    },
    "testing": {
        "template": "testing_prompt",
        "tools": _TESTING_TOOLS,
        "max_turns": 100,
        "model_tier": "testing",
        "phase": 2,
    },
    "reviewer": {
        "template": "review_prompt",
        "tools": _REVIEWER_TOOLS,
        "max_turns": 50,
        "model_tier": "coding",
        "phase": 3,
    },
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_role(name: str) -> dict[str, Any]:
    """Get a role definition by name.

    Raises:
        KeyError: If role name is not registered.
    """
    if name not in AGENT_ROLES:
        raise KeyError(
            f"Unknown agent role: '{name}'. "
            f"Available: {', '.join(AGENT_ROLES)}"
        )
    return AGENT_ROLES[name]


def get_agent_types() -> tuple[str, ...]:
    """Get all registered agent type names."""
    return tuple(AGENT_ROLES.keys())


def get_tools(name: str) -> list[str]:
    """Get MCP feature tools for an agent role."""
    return list(get_role(name)["tools"])


def get_max_turns(name: str) -> int:
    """Get max conversation turns for an agent role."""
    return get_role(name)["max_turns"]


def get_all_tools() -> list[str]:
    """Get sorted union of all agent tool lists (for permissions)."""
    all_tools: set[str] = set()
    for role in AGENT_ROLES.values():
        all_tools.update(role["tools"])
    return sorted(all_tools)


def get_template_name(name: str) -> str:
    """Get prompt template name for an agent role."""
    return get_role(name)["template"]


def get_model_tier(name: str) -> str:
    """Get model tier key for an agent role."""
    return get_role(name)["model_tier"]
