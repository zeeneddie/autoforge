# ADR-003: Data Mapping tussen MarQed, MQ Planning en MQ DevEngine

**Status:** Geaccepteerd
**Datum:** 2026-02-10
**Beslisser:** Eddie

## Context

Drie systemen moeten dezelfde werkitems representeren in hun eigen datamodel. We hebben een consistente mapping nodig die:

- Geen data verliest bij conversie
- Bidirectioneel werkt (MQ Planning <-> MQ DevEngine)
- Echo prevention ondersteunt (eigen updates niet opnieuw importeren)

## Entity Mapping

### MarQed -> MQ Planning

| MarQed (markdown) | MQ Planning Entity | Velden |
|---|---|---|
| `project.md` | **Project** | name, description, goals |
| `epic.md` | **Epic** | title, description, priority, status |
| `feature.md` | **Work Item** (parent: Epic) | title, description, story points, acceptance criteria |
| `story.md` | **Sub-Work Item** (parent: Work Item) | user story, acceptance criteria, sprint |
| `TASK-*.md` | **Sub-Work Item** of checklist | title, estimated hours |
| Dependencies | **Relations** | blocked-by / blocks |

### MQ Planning -> MQ DevEngine

| MQ Planning | MQ DevEngine Feature | Toelichting |
|---|---|---|
| **Cycle** | *(tracked als setting)* | `planning_active_cycle_id` in registry |
| **Work Item** | **Feature** | Directe 1:1 mapping |
| **Work Item title** | Feature.name | Direct |
| **Work Item description** | Feature.description | Markdown -> plain text |
| **Module name** | Feature.category | Module naam wordt category |
| **Priority** | Feature.priority | Zie priority mapping |
| **State group** | Feature.passes + in_progress | Zie state mapping |
| **Parent work item ID** | Feature.dependencies | Parent -> dependency |
| **Work Item ID** | Feature.planning_work_item_id | UUID, voor sync tracking |
| **updated_at** | Feature.planning_updated_at | Voor echo prevention |

### MQ DevEngine -> MQ Planning

| MQ DevEngine Feature | MQ Planning Work Item | Wanneer |
|---|---|---|
| in_progress=true | State -> "started" | Agent pakt feature op |
| passes=true | State -> "completed" | Feature passing |
| passes=false (na failing) | State -> "unstarted" | Feature gefaald |

## Priority Mapping

### MQ Planning -> MQ DevEngine (inbound)

| MQ Planning Priority | MQ DevEngine priority (int) |
|---|---|
| urgent | 1 |
| high | 2 |
| medium | 3 |
| low | 4 |
| none | 5 |

### MarQed -> MQ Planning

| MarQed emoji | MQ Planning Priority |
|---|---|
| CRITICAL | urgent |
| HIGH | high |
| MEDIUM | medium |
| LOW | low |

## State Mapping

### Inbound (MQ Planning -> MQ DevEngine)

| MQ Planning State Group | Feature.passes | Feature.in_progress | Actie |
|---|---|---|---|
| backlog | false | false | Importeren als nieuw |
| unstarted | false | false | Importeren als nieuw |
| started | false | true | Markeren als in progress |
| completed | true | false | Markeren als passing |
| cancelled | - | - | **Skip** (niet importeren) |

### Outbound (MQ DevEngine -> MQ Planning)

| Feature status | MQ Planning State Group target | Trigger |
|---|---|---|
| in_progress=true | started | Agent pakt feature op |
| passes=true | completed | Alle tests passen |
| passes=false (was true) | unstarted | Regressie gedetecteerd |

### State Resolution

MQ Planning heeft per project meerdere states per state group. Bij outbound sync moet MQ DevEngine de juiste state ID gebruiken:

1. Bij import: sla de state mapping op (state group -> state ID)
2. Bij outbound: zoek de eerste state in de target state group
3. Cache de mapping per project (verandert zelden)

## Echo Prevention

### Probleem

Bidirectionele sync kan loops veroorzaken:
1. MQ DevEngine updatet Feature -> pusht naar MQ Planning
2. MQ Planning's updated_at verandert
3. Volgende poll detecteert "wijziging" -> importeert opnieuw
4. Feature wordt onnodig overschreven

### Oplossing: Timestamp vergelijking

```
Na outbound push:
  1. MQ DevEngine pusht status naar MQ Planning
  2. MQ Planning API retourneert updated Work Item (met nieuwe updated_at)
  3. Sla MQ Planning's updated_at op als Feature.planning_updated_at

Bij inbound poll:
  1. Haal Work Item op van MQ Planning
  2. Vergelijk work_item.updated_at met Feature.planning_updated_at
  3. Als gelijk: eigen update -> SKIP
  4. Als verschillend: menselijke edit in MQ Planning -> SYNC
```

### Edge cases

| Situatie | Detectie | Actie |
|---|---|---|
| MQ DevEngine update + menselijke edit tegelijk | Timestamps verschillen | MQ Planning wint (menselijke edit heeft prioriteit) |
| MQ Planning work item verwijderd | 404 bij outbound push | Feature behouden in MQ DevEngine, log warning |
| Nieuw work item in MQ Planning (niet in MQ DevEngine) | Geen planning_work_item_id match | Importeren als nieuwe Feature |
| Feature verwijderd in MQ DevEngine | planning_work_item_id niet meer in DB | MQ Planning work item ongewijzigd laten |

## DB Schema Uitbreiding

### Feature tabel (bestaand + 3 nieuwe kolommen)

```sql
-- Bestaande kolommen
id              INTEGER PRIMARY KEY
priority        INTEGER DEFAULT 999
category        VARCHAR(100)
name            VARCHAR(255)
description     TEXT
steps           JSON
passes          BOOLEAN DEFAULT FALSE
in_progress     BOOLEAN DEFAULT FALSE
dependencies    JSON

-- Nieuwe kolommen (MQ Planning sync)
planning_work_item_id   VARCHAR(36) UNIQUE INDEX  -- MQ Planning UUID
planning_synced_at      DATETIME                   -- Laatste succesvolle sync
planning_updated_at     DATETIME                   -- MQ Planning's updated_at na laatste push
```

### Registry Settings (nieuw)

| Key | Type | Beschrijving |
|---|---|---|
| `planning_sync_enabled` | bool | Sync aan/uit |
| `planning_poll_interval` | int | Polling interval in seconden (default: 30) |
| `planning_active_cycle_id` | string | UUID van actieve MQ Planning cycle |

### Environment Variables (`.env`)

| Variabele | Beschrijving |
|---|---|
| `PLANNING_API_URL` | MQ Planning API base URL (bv. `http://localhost:8080`) |
| `PLANNING_API_KEY` | MQ Planning API key (gevoelig) |
| `PLANNING_WORKSPACE_SLUG` | Workspace identifier |
| `PLANNING_PROJECT_ID` | Project UUID |

## Gevolgen

- Feature tabel migratie is backward-compatible (nullable kolommen)
- Bestaande projecten zonder MQ Planning sync werken ongewijzigd
- MQ Planning sync is opt-in via `planning_sync_enabled` setting
- Rate limit budget: ~14 req/min van 60 req/min (voldoende voor <50 items per cycle)
