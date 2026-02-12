# STORY-006 | Hierarchy Tables

**Priority:** high
**Status:** planned
**Depends on:** STORY-005

Create SQLAlchemy models for `discovery_entities` (type, name, description, parent_id self-reference, session_id FK), `acceptance_criteria` (text, checked, entity_id FK), and `conversation_messages` (role, content, token_count, session_id FK). All tables use proper foreign keys with cascade deletes.

## Acceptance Criteria

- [ ] All three tables created with correct column types
- [ ] Foreign keys enforce referential integrity
- [ ] Cascade deletes propagate from session to children
- [ ] Self-referential parent_id supports nested entity hierarchies
