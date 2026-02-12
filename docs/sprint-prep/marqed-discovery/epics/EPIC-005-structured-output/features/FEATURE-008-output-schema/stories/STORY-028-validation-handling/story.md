# STORY-028 | Validation Handling

**Priority:** medium
**Status:** planned
**Depends on:** STORY-027

Implement error handling for structured output failures including automatic retry logic with exponential backoff, fallback parsing that extracts partial data from malformed responses, and user-facing error notifications with a manual retry option.

## Acceptance Criteria

- [ ] Schema parse failures trigger automatic retry up to 3 attempts
- [ ] Fallback parser extracts partial entity data from malformed JSON
- [ ] User sees a clear error message when all retries are exhausted
- [ ] Manual retry button re-sends the structured output request
