# STORY-007 | Migration System

**Priority:** high
**Status:** planned
**Depends on:** STORY-005

Set up Alembic with an initial migration that creates all tables, configure auto-generation support for detecting model changes, and document the migration CLI commands. Ensure both upgrade and downgrade paths work cleanly.

## Acceptance Criteria

- [ ] `alembic upgrade head` creates all tables from scratch
- [ ] `alembic revision --autogenerate` detects model changes
- [ ] `alembic downgrade` reverses the initial migration
- [ ] Alembic config points to the correct database URL
