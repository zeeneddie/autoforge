# STORY-014 | Streaming Handler

**Priority:** high
**Status:** planned
**Depends on:** STORY-013

Implement an SSE streaming endpoint for Claude responses that delivers tokens to the frontend in real-time. The endpoint accepts a session ID and message, streams the response token-by-token, and signals completion cleanly.

## Acceptance Criteria

- [ ] POST `/api/sessions/{id}/message` returns an SSE event stream
- [ ] Tokens arrive incrementally as Claude generates them
- [ ] Stream completes with a done event and no hanging connections
- [ ] Connection errors handled gracefully with client notification
