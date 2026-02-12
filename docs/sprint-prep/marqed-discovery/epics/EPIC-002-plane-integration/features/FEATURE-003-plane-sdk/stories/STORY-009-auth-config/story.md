# STORY-009 | Auth Config

**Priority:** high
**Status:** planned
**Depends on:** STORY-008

Configure Plane API authentication via environment variables: PLANE_API_URL, PLANE_API_KEY, and PLANE_WORKSPACE_SLUG. Add a test-connection endpoint that validates credentials against the Plane API and returns a clear error when configuration is missing or invalid.

## Acceptance Criteria

- [ ] Configuration loads from .env file via environment variables
- [ ] GET `/api/plane/test-connection` validates credentials against Plane
- [ ] Missing configuration returns a descriptive error message
- [ ] Invalid API key returns authentication failure with guidance
