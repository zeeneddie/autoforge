# STORY-021 | Message Streaming

**Priority:** high
**Status:** planned
**Depends on:** STORY-020, STORY-014

Connect the assistant-ui chat component to the SSE streaming endpoint for real-time message display. Show a typing indicator while tokens are arriving and render the complete message when the stream finishes.

## Acceptance Criteria

- [ ] Messages appear token-by-token as the SSE stream delivers them
- [ ] Typing indicator displays while Claude is generating a response
- [ ] Completed messages render with full markdown formatting
- [ ] Network disconnection shows an error state in the chat
