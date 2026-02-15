# ADR-001: MQ Planning als Project Management Frontend

**Status:** Geaccepteerd
**Datum:** 2026-02-10
**Beslisser:** Eddie

## Context

MQ DevEngine had een roadmap (Sprints 2-6) om zelf een agile planning-systeem te bouwen:

| Sprint | Onderwerp | Geschatte effort |
|--------|-----------|------------------|
| 2 | Data Model (Epic, UserStory, Sprint tabellen) | 1 sprint |
| 3 | Analyse Workflow (analyse agent, sprint planning) | 1 sprint |
| 5 | Dual Kanban Board UI | 1 sprint |
| 6 | Velocity & Metrics | 1 sprint |

Totaal: 4 sprints aan eigen PM-development.

## Beslissing

Gebruik [Plane](https://github.com/makeplane/plane) (open-source, self-hosted) als project management frontend (MQ Planning). Integreer via de REST API + webhooks.

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

### 5. MQ Planning integratie (gekozen)

- **Pro:** Self-hosted, open-source, complete PM features (epics, cycles, modules, kanban, burndown), actieve community, REST API + webhooks
- **Con:** Extra infra (Docker + PostgreSQL + Redis), twee UIs

## Rationale

1. **Enorme tijdsbesparing.** 4 sprints vervangen door 2 integratie-sprints.
2. **Betere UX.** MQ Planning is een volwassen PM tool met drag & drop, filters, burndown charts, meerdere views.
3. **Separation of concerns.** MQ Planning doet planning, MQ DevEngine doet uitvoering.
4. **Self-hosted.** Volledige controle over data en deployment.
5. **Forward-compatible.** Als we later toch eigen tabellen willen, kan de mapper aangepast worden.

## Risico's

| Risico | Impact | Mitigatie |
|--------|--------|-----------|
| Extra infra (Docker + PostgreSQL + Redis) | Medium | MQ Planning draait in Docker Compose, eenvoudige setup |
| MQ Planning downtime | Laag | Features zijn lokaal in SQLite, orchestrator werkt door |
| Rate limit (60 req/min) | Laag | Budget: ~14 req/min, voldoende voor <50 items |
| Twee UIs (MQ Planning + MQ DevEngine) | Medium | Later: deep links of embedded views |
| MQ Planning API deprecation (`/issues/` -> `/work-items/`) | Medium | Direct op nieuwe endpoints bouwen |

## Gevolgen

### Roadmap impact

**Vervalt (MQ Planning neemt over):**
- Sprint 2 (Data Model) - MQ Planning heeft Modules, Work Items, Cycles
- Sprint 3 (Analyse Workflow) - Planning gebeurt in MQ Planning
- Sprint 5 (Dual Kanban Board) - MQ Planning IS het kanban board
- Sprint 6 (Velocity & Metrics) - MQ Planning heeft ingebouwde analytics

**Blijft:**
- Sprint 1 (Multi-Model Support) - Al done
- Sprint 4 (DoD & Sprint Execution) - MQ DevEngine's kernwaarde
- Sprint 7 (Continuous Delivery) - Onafhankelijk van MQ Planning

**Nieuw:**
- Sprint 2 (nieuw): MQ Planning Integratie - Inbound sync
- Sprint 3 (nieuw): MQ Planning Integratie - Bidirectionele sync

**Resultaat: 7 sprints -> 5 sprints**

### Technische impact

- Nieuwe module: `planning_sync/` (client, mapper, sync service, webhook handler)
- 3 extra kolommen op Feature tabel (planning_work_item_id, planning_synced_at, planning_updated_at)
- Nieuwe API router: `/api/planning/*`
- MQ Planning configuratie in registry settings + `.env`
