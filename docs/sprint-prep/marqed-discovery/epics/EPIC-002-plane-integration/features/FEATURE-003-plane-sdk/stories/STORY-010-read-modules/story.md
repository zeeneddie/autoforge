# STORY-010 | Read Modules

**Priority:** high
**Status:** planned
**Depends on:** STORY-009

Implement an API endpoint to list Plane modules (epics) for a given project. Each module includes its name, description, and the count of associated work items. Handles the case where a project has no modules gracefully.

## Acceptance Criteria

- [ ] GET `/api/plane/modules` returns a list of modules for the project
- [ ] Each module includes name, description, and work item count
- [ ] Empty project returns an empty list without error
- [ ] Invalid project ID returns 404 with descriptive message
