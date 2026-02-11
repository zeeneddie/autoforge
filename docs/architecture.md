# AutoForge Systeemarchitectuur

## Overzicht

AutoForge is een autonoom coding platform dat software bouwt in agile sprint-cycli. Het systeem bestaat uit drie onafhankelijke componenten die samen een volledige analyse-planning-executie pipeline vormen:

| Component | Rol | Technologie |
|-----------|-----|-------------|
| **MarQed** | Codebase analyse, work item decompositie | Python, 11 AI agents, markdown output |
| **Plane** | Project planning, sprint management, voortgang | Self-hosted, PostgreSQL, REST API |
| **AutoForge** | Autonome code-uitvoering, testing, delivery | Python/FastAPI, Claude Agent SDK |

```
MARQED (Analyse)              PLANE (Planning)              AUTOFORGE (Executie)
+------------------------+    +------------------------+    +------------------------+
| - Codebase scanning    |    | - Backlog beheer       |    | - Feature DB (SQLite)  |
| - Gap analyse          | -> | - Sprint/Cycle planning| -> | - Orchestrator         |
| - Epic/Feature/Story   |    | - Prioritering         |    | - Coding agents        |
|   decompositie         |    | - Kanban boards        | <- | - Testing agents       |
| - Markdown output      |    | - Burndown charts      |    | - MCP server           |
+------------------------+    +------------------------+    +------------------------+
         |                            |          ^
         v                            v          |
   Git repository              +------+----------+------+
   (human review via PR)       |   PLANE SYNC SERVICE   |
                               |   (module in AutoForge) |
                               |                        |
                               |  - PlaneApiClient      |
                               |  - DataMapper          |
                               |  - Polling loop (30s)  |
                               |  - Webhook handler     |
                               |  - Release notes gen   |
                               |  - Test run tracking   |
                               +------------------------+
```

## Complete Pipeline

### Stap 1: Analyse (MarQed)

MarQed analyseert een bestaande codebase en genereert een gestructureerde breakdown:

```
Bestaande codebase + requirements
         |
         v
  MarQed AI agents scannen:
    - Welke modules/packages bestaan er?        -> Plane Modules
    - Wat zijn de grote functionele gebieden?    -> Plane Epics
    - Welke specifieke verbeteringen/features?   -> Plane Work Items
    - Welke sub-taken per work item?             -> Plane Sub-Work Items
    - Welke dependencies tussen items?           -> Plane Relations
         |
         v
  Output: Markdown bestanden in git
    project.md
      epics/EPIC-001/epic.md
        features/FEATURE-001/feature.md
          stories/STORY-001/story.md
            tasks/TASK-001.md
```

### Stap 2: Human-in-the-Loop Review (Git PR)

De markdown bestanden worden als Pull Request aangeboden:

- Mens reviewt in GitHub/Gitea met inline comments
- Kan epics splitsen, acceptance criteria aanpassen, priorities wijzigen
- PR approval = inhoudelijke goedkeuring
- Audit trail van wie wat heeft goedgekeurd

### Stap 3: Import naar Plane (MarQed -> Plane importer)

Na PR merge worden de markdown bestanden automatisch of handmatig naar Plane ge-importeerd:

```
Markdown hiërarchie    ->    Plane entiteiten
  project.md           ->    Project
  epic.md              ->    Epic
  feature.md           ->    Work Item (onder Epic)
  story.md             ->    Sub-Work Item (onder Work Item)
  TASK-*.md            ->    Sub-Work Item of checklist
  Dependencies         ->    Relations (blocked-by)
  Priority emoji       ->    Priority (urgent/high/medium/low)
  Status               ->    State (backlog/started/completed)
```

### Stap 4: Sprint Planning (Plane)

Mens organiseert werk in Plane:

- Drag & drop in cycles (sprints)
- Prioriteiten aanpassen
- Deadlines zetten
- Modules toewijzen

### Stap 5: Sprint Executie (AutoForge)

Plane Sync Service importeert de actieve cycle naar AutoForge:

```
Plane Cycle (actief)
         |
    Sync Service pollt elke 30s
         |
         v
  AutoForge Feature DB
    - Work Items -> Features
    - Priority/State/Category mapping
    - Dependencies behouden
         |
         v
  Orchestrator pakt features op
    - Coding agents implementeren
    - Testing agents verifiëren
    - Status updates terug naar Plane
```

### Stap 6: Change Document (AutoForge -> MarQed + Plane)

Na elke voltooide feature genereert AutoForge een wijzigingsdocument:

```
Feature completion
         |
         v
  AutoForge genereert change doc:
    - Gewijzigde bestanden + regelnummers
    - Git diff samenvatting
    - Acceptance criteria: voldaan/niet voldaan
    - Test resultaten
         |
         +---> Opslaan als change-doc.md in MarQed story
         +---> Pushen als comment naar Plane work item
```

## AutoForge Interne Architectuur

### Backend

- **Framework:** Python/FastAPI met uvicorn
- **Database:** SQLite per project (`{project}/.autoforge/features.db`)
- **Settings:** SQLite registry (`~/.autoforge/registry.db`)
- **CLI:** Node.js entry point (`bin/autoforge.js` -> `lib/cli.js`)

### Agent Pipeline

```
Server API -> process_manager.py -> autonomous_agent_demo.py (CLI)
                                          |
                                    parallel_orchestrator.py
                                      /        |        \
                               initializer   coding   testing
                               (agent)      (agents)  (agent)
```

- **Initializer:** Eenmalig, creëert features uit app_spec
- **Coding:** Parallel agents die features implementeren (registreert TestRun na completion)
- **Testing:** Regression tests na elke feature (registreert TestRun met batch + timing info)

### Frontend

- **Stack:** React + TypeScript + Vite + Tailwind + shadcn/ui
- **State:** React Query voor server state
- **Real-time:** WebSocket voor agent output streaming

### Plane Sync Service

```
autoforge/
  plane_sync/
    __init__.py
    client.py           # PlaneApiClient (HTTP, auth, rate limiting, write ops)
    models.py           # Pydantic modellen voor Plane API + AutoForge endpoints
    mapper.py           # Work Item <-> Feature conversie, AC parsing
    sync_service.py     # import_cycle + outbound_sync (bidirectional)
    background.py       # PlaneSyncLoop: asyncio polling, sprint detection
    completion.py       # Sprint completion: DoD, retrospective, git tag, release notes
    release_notes.py    # Markdown release notes generator
    webhook_handler.py  # HMAC-SHA256 verificatie + event parsing
    self_host.py        # Self-hosting: register AutoForge in eigen registry
```

### MarQed Import Module

```
autoforge/
  marqed_import/
    __init__.py         # Package exports
    parser.py           # parse_marqed_tree(): directory tree -> MarQedEntity tree
    models.py           # Pydantic modellen: MarQedImportRequest/Result
    importer.py         # import_to_plane(): MarQedEntity tree -> Plane modules + work items
```

De MarQed importer parseert MarQed markdown directory trees en creëert de corresponderende
Plane entiteiten:

| MarQed entity | Plane entity | Rationale |
|---|---|---|
| Epic | Module | Modules bieden grouping + status |
| Feature | Work Item | Direct mapping |
| Story | Sub-Work Item (parent=feature) | Via `parent` field |
| Task | Sub-Work Item (parent=story) | Via `parent` field |
| Dependencies | In description | Plane API v1 heeft geen relations endpoint |

### Test History

Het `TestRun` model in `api/database.py` registreert per-feature, per-agent test resultaten:

- **Recording:** De orchestrator schrijft `TestRun` rows na elke agent completion (testing + coding)
- **Batch tracking:** `feature_ids_in_batch` legt vast welke features samen getest werden
- **API:** `GET /api/plane/test-report?project_name=X` aggregeert pass/fail rates (`all_features=true` voor alle features)
- **History API:** `GET /api/plane/test-history` retourneert individuele TestRun records voor heatmap/timeline
- **Sprint stats:** `total_test_runs` en `overall_pass_rate` in sync status

### Analytics Dashboard

De UI biedt een Analytics view als derde view-modus naast Kanban en Dependency Graph:

- **ViewToggle:** `kanban | graph | analytics`, keyboard shortcut `I`
- **Test Report tab:** Summary cards (totaal, getest, pass rate, runs) + feature tabel met pass rate bars + expandable heatmap per feature (groen/rood cellen)
- **Sprint Metrics tab:** Sprint voortgang, test activiteit, feature velocity, sync status — combineert `usePlaneSyncStatus()` + `useTestReport()`
- **Release Notes tab:** Twee-paneel layout (bestandslijst + inhoud viewer) met ingebouwde markdown renderer (headers, bold, italic, lists, tables, code blocks — geen externe deps)

```
ui/src/components/
  AnalyticsDashboard.tsx    # Container met 3 tabs
  TestReportPanel.tsx       # Test results tabel + heatmap
  SprintMetricsPanel.tsx    # Sprint voortgang + test activiteit
  ReleaseNotesViewer.tsx    # Release notes lijst + viewer
```

### Webhooks

Naast de polling loop ondersteunt AutoForge ook real-time webhooks van Plane:

- **Endpoint:** `POST /api/plane/webhooks` (exempt van localhost middleware)
- **Authenticatie:** HMAC-SHA256 verificatie met configureerbaar secret
- **Dedup:** 5-seconde cooldown per event key voorkomt dubbele verwerking
- **Events:** `issue.update` en `cycle.update` triggeren `import_cycle()` voor de actieve cycle

## Deployment

### Minimaal (alleen AutoForge)

- AutoForge server + UI
- Claude Code CLI (of Anthropic API key)
- Optioneel: OpenRouter voor multi-model support

### Volledig (MarQed + Plane + AutoForge)

| Service | Vereisten | Port |
|---------|-----------|------|
| MarQed | Python 3.12+, Docker, ChromaDB | 8000 |
| Plane | Docker Compose (PostgreSQL, Redis, MinIO) | 8080 |
| AutoForge | Python 3.11+, Node.js 20+ | 5175 |

Alle drie self-hosted, volledige controle over data.
