# STORY-027 | Structured API Call

**Priority:** medium
**Status:** planned
**Depends on:** STORY-026, STORY-013

Implement a Claude API call with structured output mode (strict: true) that returns validated Epic, Feature, and Story entities. The call sends the schema definition and receives a response that parses directly into typed Python and TypeScript models.

## Acceptance Criteria

- [ ] Claude API call uses strict schema enforcement
- [ ] Response parses into typed Pydantic entity models
- [ ] Invalid or malformed responses are rejected by the schema
- [ ] Structured call supports all three entity types
