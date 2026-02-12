# STORY-011 | Read Work Items

**Priority:** high
**Status:** planned
**Depends on:** STORY-009

Implement an API endpoint to list Plane work items (features) with their state, priority, description, and parent module. Support optional filtering by module to allow loading items for a specific epic.

## Acceptance Criteria

- [ ] GET `/api/plane/work-items` returns work items with state and priority
- [ ] Each item includes description and parent module reference
- [ ] Optional module_id query parameter filters by parent module
- [ ] Large item lists paginate correctly
