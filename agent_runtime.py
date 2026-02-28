"""
Agent Runtime Abstraction
=========================

Single point of contact with the Claude Agent SDK.

Every other module in the codebase consumes the AgentClient protocol and
the RuntimeConfig / HookSpec data classes defined here.  Swapping to a
different runtime (Pi Agent SDK, local LLM, ...) means changing only
this file -- nothing else.
"""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import HookMatcher, ResultMessage

# ---------------------------------------------------------------------------
# Public protocol -- what agent.py and chat sessions consume
# ---------------------------------------------------------------------------


@runtime_checkable
class AgentClient(Protocol):
    """Minimal async-context-manager interface for an agent runtime."""

    async def __aenter__(self) -> AgentClient: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool: ...

    async def query(self, message: str | AsyncIterable[dict[str, Any]]) -> None: ...
    async def receive_response(self) -> AsyncIterator[Any]: ...
    async def get_mcp_status(self) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# SDK-agnostic hook definition
# ---------------------------------------------------------------------------


@dataclass
class HookSpec:
    """Runtime-agnostic hook specification.

    Parameters
    ----------
    event : str
        Hook event name, e.g. ``"PreToolUse"`` or ``"PreCompact"``.
    matcher : str | None
        Tool name to match (e.g. ``"Bash"``), or ``None`` for all tools.
    callback : Callable
        Async callable ``(input_data, tool_use_id, context) -> dict``.
    """

    event: str
    matcher: str | None
    callback: Callable[..., Awaitable[dict[str, Any]]]


# ---------------------------------------------------------------------------
# SDK-agnostic runtime configuration
# ---------------------------------------------------------------------------


@dataclass
class RuntimeConfig:
    """Everything needed to spin up an agent runtime -- no SDK types."""

    model: str
    cwd: Path
    settings_path: Path
    allowed_tools: list[str]
    mcp_servers: dict[str, dict[str, Any]]
    system_prompt: str | None = None
    permission_mode: str | None = None
    hooks: list[HookSpec] = field(default_factory=list)
    max_turns: int | None = None
    max_buffer_size: int | None = None
    env: dict[str, str] = field(default_factory=dict)
    setting_sources: list[str] | None = None
    betas: list[str] = field(default_factory=list)
    cli_path: str | None = None


# ---------------------------------------------------------------------------
# Claude Agent SDK implementation
# ---------------------------------------------------------------------------


class ClaudeAgentRuntime:
    """Wraps ``ClaudeSDKClient`` behind the ``AgentClient`` protocol."""

    def __init__(self, config: RuntimeConfig) -> None:
        self._config = config
        self._client: ClaudeSDKClient | None = None

    # -- async context manager ------------------------------------------------

    async def __aenter__(self) -> ClaudeAgentRuntime:
        cfg = self._config

        # Convert HookSpec list -> SDK hooks dict
        hooks_dict: dict[str, list[HookMatcher]] = {}
        for hs in cfg.hooks:
            if hs.matcher:
                matcher = HookMatcher(matcher=hs.matcher, hooks=[hs.callback])
            else:
                matcher = HookMatcher(hooks=[hs.callback])
            hooks_dict.setdefault(hs.event, []).append(matcher)

        options = ClaudeAgentOptions(
            model=cfg.model,
            cwd=str(cfg.cwd),
            settings=str(cfg.settings_path),
            allowed_tools=cfg.allowed_tools,
            mcp_servers=cfg.mcp_servers,  # type: ignore[arg-type]
            hooks=hooks_dict if hooks_dict else None,  # type: ignore[arg-type]
            max_turns=cfg.max_turns,
            max_buffer_size=cfg.max_buffer_size,
            env=cfg.env if cfg.env else None,
            setting_sources=cfg.setting_sources,
            betas=cfg.betas if cfg.betas else None,
            cli_path=cfg.cli_path,
            system_prompt=cfg.system_prompt,
            permission_mode=cfg.permission_mode,
        )

        self._client = ClaudeSDKClient(options=options)
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        if self._client:
            return await self._client.__aexit__(exc_type, exc_val, exc_tb)
        return False

    # -- forwarding methods ---------------------------------------------------

    async def query(self, message: str | AsyncIterable[dict[str, Any]]) -> None:
        assert self._client is not None, "Runtime not entered (use async with)"
        await self._client.query(message)

    async def receive_response(self) -> AsyncIterator[Any]:
        assert self._client is not None, "Runtime not entered (use async with)"
        async for msg in self._client.receive_response():
            yield msg

    async def get_mcp_status(self) -> dict[str, Any]:
        assert self._client is not None, "Runtime not entered (use async with)"
        return await self._client.get_mcp_status()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_runtime(config: RuntimeConfig) -> AgentClient:
    """Create an agent runtime from an SDK-agnostic config."""
    return ClaudeAgentRuntime(config)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_result_message(msg: Any) -> bool:
    """Check if a message is a ResultMessage without importing SDK types."""
    return isinstance(msg, ResultMessage)
