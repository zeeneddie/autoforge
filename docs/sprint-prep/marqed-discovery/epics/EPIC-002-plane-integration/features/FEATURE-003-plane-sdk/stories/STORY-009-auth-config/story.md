# STORY-009 | Auth Config

**Priority:** high
**Status:** planned
**Depends on:** STORY-008

Configure MQ Planning API authentication via environment variables: PLANNING_API_URL, PLANNING_API_KEY, and PLANNING_WORKSPACE_SLUG. Add a test-connection endpoint that validates credentials against the MQ Planning API and returns a clear error when configuration is missing or invalid.

## Acceptance Criteria

- [ ] Configuration loads from .env file via environment variables
- [ ] GET `/api/planning/test-connection` validates credentials against MQ Planning
- [ ] Missing configuration returns a descriptive error message
- [ ] Invalid API key returns authentication failure with guidance
