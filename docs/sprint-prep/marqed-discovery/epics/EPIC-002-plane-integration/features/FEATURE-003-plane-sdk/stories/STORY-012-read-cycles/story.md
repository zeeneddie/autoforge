# STORY-012 | Read Cycles

**Priority:** high
**Status:** planned
**Depends on:** STORY-009

Implement an API endpoint to list MQ Planning cycles (sprints) with their name, start and end dates, and the IDs of assigned work items. This enables the discovery tool to understand sprint context when operating in brownpaper mode.

## Acceptance Criteria

- [ ] GET `/api/planning/cycles` returns a list of cycles for the project
- [ ] Each cycle includes name, start date, end date, and status
- [ ] Assigned work item IDs included in each cycle response
- [ ] Completed and active cycles both appear in the list
