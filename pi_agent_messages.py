"""
Pi Agent Message Translation (JSON Patch Protocol)
===================================================

Translates between Pi Agent JSON-RPC messages and the message types
that agent.py expects (matching the Claude Agent SDK interface).

Uses JSON Patch (RFC 6902) for incremental message updates, reducing
bandwidth for streaming responses. Full messages are sent as initial
state; subsequent updates are patches.

Message flow:
  Pi Agent stdout → JSON line → translate → PiAssistantMessage / PiResultMessage
  agent.py query  → translate → JSON line → Pi Agent stdin
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field  # noqa: F401 -- field used in dataclasses
from typing import Any

# ---------------------------------------------------------------------------
# JSON Patch helpers (RFC 6902 subset)
# ---------------------------------------------------------------------------


@dataclass
class JsonPatchOp:
    """Single JSON Patch operation."""

    op: str  # "add" | "replace" | "remove"
    path: str  # JSON Pointer (e.g. "/content/0/text")
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"op": self.op, "path": self.path}
        if self.op != "remove":
            d["value"] = self.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> JsonPatchOp:
        return cls(op=d["op"], path=d["path"], value=d.get("value"))


def apply_patch(doc: dict[str, Any], ops: list[JsonPatchOp]) -> dict[str, Any]:
    """Apply a list of JSON Patch operations to a document.

    Supports a minimal subset: /key, /key/index, /key/index/subkey.
    Enough for streaming text content and tool results.
    """
    for op in ops:
        parts = op.path.strip("/").split("/")
        if not parts or parts == [""]:
            continue

        target = doc
        for part in parts[:-1]:
            if isinstance(target, list):
                target = target[int(part)]
            else:
                target = target[part]

        last = parts[-1]
        if isinstance(target, list):
            idx = int(last) if last != "-" else len(target)
            if op.op == "add":
                if last == "-":
                    target.append(op.value)
                else:
                    target.insert(idx, op.value)
            elif op.op == "replace":
                target[idx] = op.value
            elif op.op == "remove":
                del target[idx]
        else:
            if op.op in ("add", "replace"):
                target[last] = op.value
            elif op.op == "remove":
                target.pop(last, None)

    return doc


# ---------------------------------------------------------------------------
# Message wrapper types (duck-type compatible with Claude SDK messages)
# ---------------------------------------------------------------------------


@dataclass
class PiTextBlock:
    """Text content block from Pi Agent."""

    text: str
    type: str = "text"


@dataclass
class PiToolUseBlock:
    """Tool use request from Pi Agent."""

    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class PiToolResultBlock:
    """Tool result to send back to Pi Agent."""

    tool_use_id: str
    content: str
    is_error: bool = False
    type: str = "tool_result"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "tool_use_id": self.tool_use_id,
            "content": self.content,
            "is_error": self.is_error,
        }


@dataclass
class PiAssistantMessage:
    """Assistant message from Pi Agent (maps to SDK AssistantMessage)."""

    content: list[PiTextBlock | PiToolUseBlock] = field(default_factory=list)
    role: str = "assistant"
    stop_reason: str | None = None


@dataclass
class PiResultMessage:
    """End-of-session signal (maps to SDK ResultMessage)."""

    subtype: str = "result"
    cost_usd: float = 0.0
    duration_ms: int = 0
    duration_api_ms: int = 0
    is_error: bool = False
    num_turns: int = 0
    session_id: str = ""


# ---------------------------------------------------------------------------
# Translation functions
# ---------------------------------------------------------------------------


def translate_pi_response(json_msg: dict[str, Any]) -> PiAssistantMessage | PiResultMessage | None:
    """Translate a Pi Agent JSON-RPC response to a typed message.

    Pi Agent protocol messages:
      {"type": "assistant", "content": [...]}  → PiAssistantMessage
      {"type": "result", ...}                  → PiResultMessage
      {"type": "patch", "ops": [...]}          → Apply patch (stateful, returns None)

    Returns:
        Translated message, or None for patch-only updates.
    """
    msg_type = json_msg.get("type", "")

    if msg_type == "assistant":
        content = []
        for block in json_msg.get("content", []):
            block_type = block.get("type", "text")
            if block_type == "text":
                content.append(PiTextBlock(text=block.get("text", "")))
            elif block_type == "tool_use":
                content.append(PiToolUseBlock(
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    input=block.get("input", {}),
                ))
        return PiAssistantMessage(
            content=content,
            stop_reason=json_msg.get("stop_reason"),
        )

    if msg_type == "result":
        return PiResultMessage(
            cost_usd=json_msg.get("cost_usd", 0.0),
            duration_ms=json_msg.get("duration_ms", 0),
            duration_api_ms=json_msg.get("duration_api_ms", 0),
            is_error=json_msg.get("is_error", False),
            num_turns=json_msg.get("num_turns", 0),
            session_id=json_msg.get("session_id", ""),
        )

    return None


def build_query_message(message: str) -> str:
    """Build a JSON-RPC query message for Pi Agent stdin.

    Returns a single JSON line (no trailing newline).
    """
    return json.dumps({
        "type": "query",
        "message": message,
    })


def build_tool_result_message(tool_use_id: str, content: str, is_error: bool = False) -> str:
    """Build a JSON-RPC tool result message for Pi Agent stdin."""
    return json.dumps({
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error,
    })


def build_patch_message(ops: list[JsonPatchOp]) -> str:
    """Build a JSON Patch message (RFC 6902) for incremental updates."""
    return json.dumps({
        "type": "patch",
        "ops": [op.to_dict() for op in ops],
    })
