# STORY-003 | PostgreSQL Docker

**Priority:** high
**Status:** planned

Create a Docker Compose file with PostgreSQL 15, a persistent named volume for data durability, and environment variable configuration for the connection string. Include a .env.example file documenting required variables.

## Acceptance Criteria

- [ ] `docker compose up` starts PostgreSQL 15 container
- [ ] psql connects using configured credentials
- [ ] Data persists across container restarts via named volume
- [ ] Connection string configurable via .env file
