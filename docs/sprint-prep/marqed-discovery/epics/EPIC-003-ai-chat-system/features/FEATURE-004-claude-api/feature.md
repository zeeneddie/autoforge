# FEATURE-004 | Claude API Integration

**Priority:** high
**Status:** planned
**Depends on:** FEATURE-001

Set up the Anthropic SDK with a Claude client wrapper, implement SSE streaming for real-time token delivery, and add per-message and per-session token usage tracking. This feature provides the core AI communication layer that the phased prompt system and structured output features depend on.

## Acceptance Criteria

- [ ] Anthropic SDK installed and client authenticates
- [ ] SSE streaming endpoint delivers tokens incrementally
- [ ] Token counts tracked per message and per session
