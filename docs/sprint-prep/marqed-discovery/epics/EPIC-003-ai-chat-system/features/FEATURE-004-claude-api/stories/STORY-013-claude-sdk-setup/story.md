# STORY-013 | Claude SDK Setup

**Priority:** high
**Status:** planned

Install the Anthropic Python SDK, create a Claude client wrapper class with API key configuration via environment variable, and support model selection. Include proper error handling for authentication failures and rate limiting.

## Acceptance Criteria

- [ ] Anthropic SDK imported and client authenticates successfully
- [ ] Model configurable via ANTHROPIC_MODEL environment variable
- [ ] Authentication failure returns a clear error message
- [ ] Rate limit errors handled with appropriate retry guidance
