# EPIC-001 | Core Infrastructure

**Priority:** high
**Status:** planned

Project scaffolding, database setup, and Docker configuration. This epic establishes the foundational layer that all other epics depend on: a React frontend served by Vite, a FastAPI backend with uvicorn, a PostgreSQL database running in Docker, and the base UI component library.

## Acceptance Criteria

- [ ] Project builds successfully with no errors
- [ ] Database connects and runs migrations
- [ ] Docker compose brings up all services
- [ ] Health endpoint returns 200 OK
