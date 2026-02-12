# FEATURE-005 | Phased Prompts

**Priority:** high
**Status:** planned
**Depends on:** FEATURE-004

Implement the six-phase prompt pipeline: Context Gathering, Scope Definition, Decomposition, Refinement, Validation, and Export. Each phase uses a distinct prompt template that guides the AI conversation. Includes brownpaper mode (loads existing Onboarding output as context) and greenpaper mode (starts from blank slate).

## Acceptance Criteria

- [ ] Phase 1 context gathering prompt works and collects project info
- [ ] Phases 2 through 6 each have structured prompt templates
- [ ] Brownpaper mode loads existing files and presents findings
- [ ] Greenpaper mode starts with open-ended questions
