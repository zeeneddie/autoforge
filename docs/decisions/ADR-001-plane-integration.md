# ADR-001: Plane als Project Management Frontend

**Status:** Geaccepteerd
**Datum:** 2026-02-10
**Beslisser:** Eddie

## Context

AutoForge had een roadmap (Sprints 2-6) om zelf een agile planning-systeem te bouwen:

| Sprint | Onderwerp | Geschatte effort |
|--------|-----------|------------------|
| 2 | Data Model (Epic, UserStory, Sprint tabellen) | 1 sprint |
| 3 | Analyse Workflow (analyse agent, sprint planning) | 1 sprint |
| 5 | Dual Kanban Board UI | 1 sprint |
| 6 | Velocity & Metrics | 1 sprint |

Totaal: 4 sprints aan eigen PM-development.

## Beslissing

Gebruik [Plane](https://github.com/makeplane/plane) (open-source, self-hosted) als project management frontend. Integreer via Plane's REST API + webhooks.

## Alternatieven Overwogen

### 1. Zelf bouwen (oorspronkelijke roadmap)

- **Pro:** Volledige controle, diep geintegreerd
- **Con:** 4 sprints effort, nooit zo feature-complete als een dedicated PM tool, onderhoudslast

### 2. Linear integratie

- **Pro:** Uitstekende UX, snelle API
- **Con:** Niet self-hosted, vendor lock-in, kosten per seat

### 3. Jira integratie

- **Pro:** Industriestandaard, rijke API
- **Con:** Complex, zwaar, niet self-hosted (tenzij Data Center), duur

### 4. GitHub Projects integratie

- **Pro:** Al onderdeel van git workflow
- **Con:** Beperkte PM features, geen echte sprint/cycle support, geen epics

### 5. Plane integratie (gekozen)

- **Pro:** Self-hosted, open-source, complete PM features (epics, cycles, modules, kanban, burndown), actieve community, REST API + webhooks
- **Con:** Extra infra (Docker + PostgreSQL + Redis), twee UIs

## Rationale

1. **Enorme tijdsbesparing.** 4 sprints vervangen door 2 integratie-sprints.
2. **Betere UX.** Plane is een volwassen PM tool met drag & drop, filters, burndown charts, meerdere views.
3. **Separation of concerns.** Plane doet planning, AutoForge doet uitvoering.
4. **Self-hosted.** Volledige controle over data en deployment.
5. **Forward-compatible.** Als we later toch eigen tabellen willen, kan de mapper aangepast worden.

## Risico's

| Risico | Impact | Mitigatie |
|--------|--------|-----------|
| Extra infra (Docker + PostgreSQL + Redis) | Medium | Plane draait in Docker Compose, eenvoudige setup |
| Plane downtime | Laag | Features zijn lokaal in SQLite, orchestrator werkt door |
| Rate limit (60 req/min) | Laag | Budget: ~14 req/min, voldoende voor <50 items |
| Twee UIs (Plane + AutoForge) | Medium | Later: deep links of embedded views |
| Plane API deprecation (`/issues/` -> `/work-items/`) | Medium | Direct op nieuwe endpoints bouwen |

## Gevolgen

### Roadmap impact

**Vervalt (Plane neemt over):**
- Sprint 2 (Data Model) - Plane heeft Modules, Work Items, Cycles
- Sprint 3 (Analyse Workflow) - Planning gebeurt in Plane
- Sprint 5 (Dual Kanban Board) - Plane IS het kanban board
- Sprint 6 (Velocity & Metrics) - Plane heeft ingebouwde analytics

**Blijft:**
- Sprint 1 (Multi-Model Support) - Al done
- Sprint 4 (DoD & Sprint Execution) - AutoForge's kernwaarde
- Sprint 7 (Continuous Delivery) - Onafhankelijk van Plane

**Nieuw:**
- Sprint 2 (nieuw): Plane Integratie - Inbound sync
- Sprint 3 (nieuw): Plane Integratie - Bidirectionele sync

**Resultaat: 7 sprints -> 5 sprints**

### Technische impact

- Nieuwe module: `plane_sync/` (client, mapper, sync service, webhook handler)
- 3 extra kolommen op Feature tabel (plane_work_item_id, plane_synced_at, plane_updated_at)
- Nieuwe API router: `/api/plane/*`
- Plane configuratie in registry settings + `.env`
