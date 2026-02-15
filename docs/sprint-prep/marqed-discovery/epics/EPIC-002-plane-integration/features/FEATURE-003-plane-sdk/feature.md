# FEATURE-003 | MQ Planning SDK

**Priority:** high
**Status:** planned
**Depends on:** FEATURE-001

Install and configure the Plane Python SDK with authenticated API access. Implement read endpoints for modules (epics), work items (features), and cycles (sprints) so the discovery tool can load existing backlog context from MQ Planning projects.

## Acceptance Criteria

- [ ] MQ Planning SDK installed and version pinned
- [ ] API authentication via environment variables
- [ ] Read modules endpoint returns module list with item counts
- [ ] Read work items endpoint returns items with state and priority
- [ ] Read cycles endpoint returns cycles with date ranges
