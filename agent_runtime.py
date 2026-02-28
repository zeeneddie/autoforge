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

import shutil
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
    runtime_type: str = "claude"  # "claude" | "pi-agent"


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
# Pi Agent Runtime (stub -- RPC bridge comes in Fase 2)
# ---------------------------------------------------------------------------


class PiAgentRuntime:
    """Pi Agent behind the AgentClient protocol (RPC mode).

    Communicates with a Pi Agent subprocess via JSON lines over stdin/stdout.
    Uses JSON Patch (RFC 6902) for incremental streaming updates.
    Supports git worktree isolation for parallel agent execution.
    """

    def __init__(self, config: RuntimeConfig, agent_id: str | None = None) -> None:
        self._config = config
        self._agent_id = agent_id
        self._bridge: Any | None = None  # PiAgentProcess (lazy import)
        self._worktree_path: Path | None = None

    async def __aenter__(self) -> PiAgentRuntime:
        if not shutil.which("pi-agent") and not shutil.which("npx"):
            raise RuntimeError(
                "Pi Agent niet gevonden op PATH. "
                "Installeer met: npm install -g pi-agent"
            )

        import os

        from pi_agent_bridge import PiAgentProcess

        # Optional git worktree isolation for parallel agents
        worktree_dir: Path | None = None
        use_worktree = os.getenv("PI_AGENT_WORKTREE", "false").lower() in ("true", "1", "yes")
        if use_worktree and self._agent_id:
            try:
                from worktree_manager import create_worktree
                worktree_dir = await create_worktree(self._config.cwd, self._agent_id)
                self._worktree_path = worktree_dir
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to create worktree for agent '%s': %s", self._agent_id, e
                )

        self._bridge = PiAgentProcess(
            project_dir=self._config.cwd,
            model=os.getenv("PI_AGENT_MODEL"),
            provider=os.getenv("PI_AGENT_PROVIDER"),
            pi_agent_path=os.getenv("PI_AGENT_PATH"),
            env=self._config.env,
            worktree_dir=worktree_dir,
        )
        await self._bridge.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        if self._bridge:
            await self._bridge.stop()
            self._bridge = None

        # Clean up worktree (merge changes first, then remove)
        if self._worktree_path and self._agent_id:
            try:
                from worktree_manager import cleanup_worktree, merge_worktree
                await merge_worktree(self._config.cwd, self._agent_id)
                await cleanup_worktree(self._config.cwd, self._agent_id)
            except Exception:
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to cleanup worktree for agent '%s'", self._agent_id,
                    exc_info=True,
                )
            self._worktree_path = None

        return False

    async def query(self, message: str | AsyncIterable[dict[str, Any]]) -> None:
        assert self._bridge is not None, "Runtime not entered (use async with)"
        if isinstance(message, str):
            await self._bridge.send_query(message)
        else:
            # AsyncIterable -- collect and send as single message
            parts: list[str] = []
            async for chunk in message:
                if isinstance(chunk, dict) and "text" in chunk:
                    parts.append(chunk["text"])
            await self._bridge.send_query("".join(parts) if parts else "")

    async def receive_response(self) -> AsyncIterator[Any]:
        assert self._bridge is not None, "Runtime not entered (use async with)"

        from pi_agent_messages import PiAssistantMessage, PiResultMessage, PiToolUseBlock

        async for msg in self._bridge.receive():
            if isinstance(msg, PiAssistantMessage):
                # Check for tool_use blocks -- intercept and execute via tool proxy
                has_tool_use = any(
                    isinstance(block, PiToolUseBlock) for block in msg.content
                )
                if has_tool_use:
                    for block in msg.content:
                        if isinstance(block, PiToolUseBlock):
                            # Execute tool via proxy (Fase 3)
                            result = await self._execute_tool(block)
                            await self._bridge.send_tool_result(
                                tool_use_id=block.id,
                                content=result.get("content", ""),
                                is_error=result.get("is_error", False),
                            )
                yield msg

            elif isinstance(msg, PiResultMessage):
                yield msg
                return

    async def get_mcp_status(self) -> dict[str, Any]:
        return {"mcpServers": []}

    async def _execute_tool(self, block: Any) -> dict[str, Any]:
        """Execute a tool call from Pi Agent via the tool proxy.

        Falls back to a not-implemented error if pi_agent_tools is not available.
        """
        try:
            from pi_agent_tools import execute_tool
            return await execute_tool(block.name, block.input, self._config.cwd)
        except ImportError:
            return {
                "content": f"Tool proxy niet beschikbaar voor '{block.name}'. Fase 3 vereist.",
                "is_error": True,
            }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_runtime(config: RuntimeConfig) -> AgentClient:
    """Create an agent runtime from an SDK-agnostic config."""
    if config.runtime_type == "pi-agent":
        return PiAgentRuntime(config)  # type: ignore[return-value]
    return ClaudeAgentRuntime(config)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_result_message(msg: Any) -> bool:
    """Check if a message is a ResultMessage without importing SDK types.

    Supports both Claude SDK ResultMessage and PiResultMessage.
    """
    if isinstance(msg, ResultMessage):
        return True
    # Duck-type check for PiResultMessage (avoids circular import)
    return getattr(msg, "subtype", None) == "result"
