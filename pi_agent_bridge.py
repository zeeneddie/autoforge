"""
Pi Agent RPC Bridge
===================

Manages a Pi Agent subprocess in RPC mode, communicating via
JSON lines over stdin/stdout.

The bridge handles:
- Process lifecycle (start, stop, health check)
- Message framing (one JSON object per line)
- Async iteration over response messages
- Tool call interception and result injection

Protocol:
  → stdin:  {"type": "query", "message": "..."} or {"type": "tool_result", ...}
  ← stdout: {"type": "assistant", "content": [...]} or {"type": "result", ...}

Uses JSON Patch (RFC 6902) for incremental streaming updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, AsyncIterator

from pi_agent_messages import (
    PiAssistantMessage,
    PiResultMessage,
    build_query_message,
    build_tool_result_message,
    translate_pi_response,
)

logger = logging.getLogger(__name__)

# Default timeout for Pi Agent process startup
STARTUP_TIMEOUT_S = 30

# Default timeout for receiving a response line
RECEIVE_TIMEOUT_S = 300  # 5 minutes


class PiAgentProcess:
    """Manages a pi-agent subprocess in RPC mode.

    Usage::

        async with PiAgentProcess(project_dir=Path("/my/project")) as pi:
            await pi.send_query("Implement the login feature")
            async for msg in pi.receive():
                if isinstance(msg, PiResultMessage):
                    break
                print(msg)
    """

    def __init__(
        self,
        project_dir: Path,
        model: str | None = None,
        provider: str | None = None,
        pi_agent_path: str | None = None,
        env: dict[str, str] | None = None,
        worktree_dir: Path | None = None,
    ) -> None:
        self._project_dir = project_dir
        self._model = model or os.getenv("PI_AGENT_MODEL", "gpt-4o")
        self._provider = provider or os.getenv("PI_AGENT_PROVIDER", "openai")
        self._pi_agent_path = pi_agent_path or os.getenv("PI_AGENT_PATH", "pi-agent")
        self._env = env or {}
        self._worktree_dir = worktree_dir  # Git worktree for isolation (Fase 3)
        self._process: asyncio.subprocess.Process | None = None
        self._started = False

    @property
    def cwd(self) -> Path:
        """Working directory for the Pi Agent process."""
        return self._worktree_dir or self._project_dir

    async def __aenter__(self) -> PiAgentProcess:
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        await self.stop()
        return False

    async def start(self) -> None:
        """Spawn the pi-agent process in RPC mode."""
        cmd = self._build_command()
        logger.info("Starting Pi Agent: %s (cwd=%s)", " ".join(cmd), self.cwd)

        # Merge environment: inherit parent + custom overrides
        proc_env = {**os.environ, **self._env}

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.cwd),
            env=proc_env,
        )

        # Wait for ready signal (first line from stdout)
        try:
            ready_line = await asyncio.wait_for(
                self._read_line(),
                timeout=STARTUP_TIMEOUT_S,
            )
            if ready_line:
                ready_msg = json.loads(ready_line)
                if ready_msg.get("type") == "ready":
                    logger.info("Pi Agent ready (pid=%s)", self._process.pid)
                    self._started = True
                    return
                # Not a ready message -- treat as first response
                logger.warning("Pi Agent first message was not 'ready': %s", ready_line[:200])
                self._started = True
        except asyncio.TimeoutError:
            logger.warning("Pi Agent startup timed out after %ds", STARTUP_TIMEOUT_S)
            await self.stop()
            raise RuntimeError(f"Pi Agent failed to start within {STARTUP_TIMEOUT_S}s")

    async def stop(self) -> None:
        """Gracefully stop the Pi Agent process."""
        if self._process is None:
            return

        if self._process.returncode is None:
            # Send shutdown signal
            try:
                shutdown = json.dumps({"type": "shutdown"}) + "\n"
                self._process.stdin.write(shutdown.encode())  # type: ignore[union-attr]
                await self._process.stdin.drain()  # type: ignore[union-attr]
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

            # Wait briefly for graceful shutdown
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Pi Agent did not exit gracefully, terminating")
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    self._process.kill()

        self._process = None
        self._started = False

    async def send_query(self, message: str) -> None:
        """Send a query message to Pi Agent."""
        self._assert_running()
        line = build_query_message(message) + "\n"
        self._process.stdin.write(line.encode())  # type: ignore[union-attr]
        await self._process.stdin.drain()  # type: ignore[union-attr]
        logger.debug("Sent query to Pi Agent (%d chars)", len(message))

    async def send_tool_result(
        self, tool_use_id: str, content: str, is_error: bool = False
    ) -> None:
        """Send a tool execution result back to Pi Agent."""
        self._assert_running()
        line = build_tool_result_message(tool_use_id, content, is_error) + "\n"
        self._process.stdin.write(line.encode())  # type: ignore[union-attr]
        await self._process.stdin.drain()  # type: ignore[union-attr]
        logger.debug("Sent tool result for %s (error=%s)", tool_use_id, is_error)

    async def receive(self) -> AsyncIterator[PiAssistantMessage | PiResultMessage]:
        """Async iterator over Pi Agent response messages.

        Yields PiAssistantMessage for content/tool-use, PiResultMessage for session end.
        """
        self._assert_running()
        while True:
            try:
                line = await asyncio.wait_for(
                    self._read_line(),
                    timeout=RECEIVE_TIMEOUT_S,
                )
            except asyncio.TimeoutError:
                logger.error("Pi Agent response timeout (%ds)", RECEIVE_TIMEOUT_S)
                yield PiResultMessage(is_error=True)
                return

            if line is None:
                # Process ended
                logger.info("Pi Agent process ended")
                yield PiResultMessage(is_error=self._process.returncode != 0 if self._process else True)
                return

            try:
                json_msg = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Non-JSON line from Pi Agent: %s", line[:200])
                continue

            msg = translate_pi_response(json_msg)
            if msg is None:
                continue  # Patch-only or unrecognized message

            yield msg

            if isinstance(msg, PiResultMessage):
                return

    @property
    def is_running(self) -> bool:
        """Check if the Pi Agent process is still running."""
        return (
            self._process is not None
            and self._process.returncode is None
            and self._started
        )

    # -- private helpers ------------------------------------------------------

    def _build_command(self) -> list[str]:
        """Build the command to start pi-agent in RPC mode."""
        # Try direct binary first, fall back to npx
        if shutil.which(self._pi_agent_path):
            cmd = [self._pi_agent_path]
        elif shutil.which("npx"):
            cmd = ["npx", self._pi_agent_path]
        else:
            raise RuntimeError(
                f"Cannot find '{self._pi_agent_path}' or 'npx' on PATH. "
                "Install Pi Agent with: npm install -g pi-agent"
            )

        cmd.extend(["--mode", "rpc"])

        if self._model:
            cmd.extend(["--model", self._model])
        if self._provider:
            cmd.extend(["--provider", self._provider])

        return cmd

    def _assert_running(self) -> None:
        """Assert that the process is running."""
        if not self.is_running:
            raise RuntimeError("Pi Agent process is not running")

    async def _read_line(self) -> str | None:
        """Read a single line from Pi Agent stdout.

        Returns None if the process has ended (EOF).
        """
        if self._process is None or self._process.stdout is None:
            return None

        try:
            line = await self._process.stdout.readline()
            if not line:
                return None  # EOF
            return line.decode().strip()
        except (OSError, ValueError):
            return None
