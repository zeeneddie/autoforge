# STORY-005 | Session Models

**Priority:** high
**Status:** planned
**Depends on:** STORY-003

Create SQLAlchemy models for the `sessions` table with columns for id (UUID primary key), name, mode (brownpaper or greenpaper enum), status, created_at, updated_at, and plane_project_id. Include proper indexing and enum validation.

## Acceptance Criteria

- [ ] Session model creates the sessions table on migrate
- [ ] CRUD operations work for create, read, update, delete
- [ ] Mode enum validates only brownpaper and greenpaper values
- [ ] Timestamps auto-populate on create and update
