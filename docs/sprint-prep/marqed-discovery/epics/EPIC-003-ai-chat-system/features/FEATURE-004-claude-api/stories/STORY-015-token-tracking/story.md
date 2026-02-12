# STORY-015 | Token Tracking

**Priority:** high
**Status:** planned
**Depends on:** STORY-013

Track input and output token counts per message and aggregate totals per session. Store counts in the conversation_messages table and expose a usage summary endpoint for monitoring costs and staying within budget.

## Acceptance Criteria

- [ ] Input and output token counts stored per conversation message
- [ ] Session total token usage aggregated from all messages
- [ ] GET `/api/sessions/{id}/usage` returns token count summary
- [ ] Token counts match Anthropic API response metadata
