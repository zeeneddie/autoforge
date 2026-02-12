# STORY-002 | FastAPI Structure

**Priority:** high
**Status:** planned
**Depends on:** STORY-001

Create a FastAPI application with uvicorn, a modular router structure, CORS middleware configured for the frontend origin, and a health check endpoint. The application should follow a clean separation of routers, services, and schemas.

## Acceptance Criteria

- [ ] `uvicorn` starts the server on localhost:8000
- [ ] GET `/api/health` returns 200 with status payload
- [ ] CORS middleware allows requests from localhost:5173
- [ ] Router structure supports modular endpoint registration
