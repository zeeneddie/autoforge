# FEATURE-002 | Database Schema

**Priority:** high
**Status:** planned
**Depends on:** FEATURE-001

Design and implement the SQLAlchemy data models for sessions, discovery entities, acceptance criteria, and conversation messages. Includes Alembic migration setup for schema versioning. The schema supports brownpaper and greenpaper session modes, hierarchical entity trees with foreign keys, and full conversation history.

## Acceptance Criteria

- [ ] All tables created via Alembic migrations
- [ ] Migrations run forward and backward cleanly
- [ ] CRUD operations work for all models
