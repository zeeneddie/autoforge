# MarQed.ai Systeemarchitectuur

## Overzicht

Het **MarQed.ai platform** bestaat uit vijf componenten die samen een volledige onboarding-discovery-planning-executie-feedback pipeline vormen:

| Component | Rol | Technologie | Doelgroep |
|-----------|-----|-------------|-----------|
| **Onboarding** | Codebase analyse, kennis opbouw, IFPUG functiepunten | Python, 11 AI agents, markdown output | Developer, Tech Lead |
| **Discovery Tool** | Requirements gathering: brownpaper (bestaand) en greenpaper (nieuwbouw) | React/assistant-ui, FastAPI, PostgreSQL | Product Manager, Stakeholder |
| **PM Dashboard** | Hiërarchisch overzicht met drill-down en metriek | React, Aggregatie API | Product Manager |
| **Plane** | Planning, backlog, sprint management (SSOT) | Self-hosted, PostgreSQL, REST API | Product Manager, Developer |
| **MQ DevEngine** | Autonome code-uitvoering, testing, delivery | Python/FastAPI, Claude Agent SDK | Developer |

Zie [platform-overview.md](platform-overview.md) voor het volledige platformdiagram met alle datastromen.

```
MarQed.ai Platform
+---------------------------------------------------------------------------+
|                                                                           |
|  ONBOARDING            DISCOVERY TOOL               PM DASHBOARD          |
|  (Codebase Analyse)    (Requirements)               (Monitoring)          |
|  +----------------+    +----------------------+     +------------------+  |
|  | Codebase scan  |    | Brownpaper:          |     | App > Epic >     |  |
|  | Gap analyse    |--->|  bevestig onboarding |     |  Feature > Story |  |
|  | Kennis opbouw  |    |  docu wat er is      |     |                  |  |
|  | IFPUG FP       |    |  + interview         |     | Per niveau:      |  |
|  |                |    |                      |     |  children, FP,   |  |
|  |                |    | Greenpaper:          |     |  tests, fase     |  |
|  |                |    |  nieuwbouw           |     |                  |  |
|  |                |    |  docu + interview    |     | CRUD: R / CR / F |  |
|  +-------+--------+    +----------+-----------+     +--+----+----+-----+  |
|          |                        |                    |    |    |        |
|          | IFPUG FP               | schrijft           |    |    |        |
|          | + kennis               | naar               |    |    |        |
|          |                        |                    |    |    |        |
|          |       +================+================+   |    |    |        |
|          |       ||        PLANE (SSOT)            ||--+    |    |        |
|          |       ||  Backlog, Cycles, Modules      || hierarchie |        |
|          |       ||  Prioritering, Voortgang       || + states   |        |
|          |       +================+====+===========+        |    |        |
|          |                  import |    ^ status            |    |        |
|          |                        v    | + feedback         |    |        |
|          |       +---------------------+---+                |    |        |
|          |       |      MQ DEVENGINE        |----------------+    |        |
|          |       |     Coding + Testing    |  test results       |        |
|          |       +-------------------------+                     |        |
|          |                                                       |        |
|          +-------------------------------------------------------+        |
|                         IFPUG FP                                          |
|                                                                           |
+---------------------------------------------------------------------------+
```

## Ontwerpprincipes

### 1. Mens als regisseur

De AI doet het zware werk (analyseren, genereren, bouwen, testen). De mens maakt **alle GO/NO-GO beslissingen**. Geen enkel item mag automatisch van Discovery naar Plane of van Plane naar productie zonder menselijke goedkeuring.

### 2. Plane is Single Source of Truth

Plane is de enige bron van waarheid voor alle work items. De Discovery Tool is ephemeer (sessie resulteert in Plane items). Onboarding is referentiemateriaal. MQ DevEngine leest uit en schrijft terug naar Plane. Geen dubbele administratie.

### 3. Micro features: maximaal 2 uur bouwen + testen

Elke feature moet klein genoeg zijn om binnen 2 uur gebouwd en getest te worden. Dit zorgt ervoor dat:
- Gebruikers snel resultaat zien en kunnen beoordelen
- Feedback sneller terugkomt
- Er nooit lang aan het verkeerde wordt gewerkt
- Falen goedkoop is

### 4. Snel en vaak falen, kort cyclisch werken

Korte cycles, snelle feedback. Als iets niet klopt, wordt het binnen uren ontdekt — niet na dagen. De Discovery Tool decomposeert werk tot micro features. MQ DevEngine bouwt ze snel. De PM beoordeelt snel. Afwijzingen gaan direct terug de Discovery in.

### 5. Feedback loop sluit altijd

De pipeline is cyclisch, niet lineair:
- Test resultaten → Plane work item comment
- PM reviewt → goedkeuren of afwijzen met feedback
- Afgewezen items → terug naar Discovery met context
- Verfijnde requirements → opnieuw naar Plane → opnieuw bouwen

Geen dood spoor. Elke uitkomst leidt tot een volgende actie.

### 6. Separation of duties

Elk tool heeft precies één verantwoordelijkheid:
- **Onboarding**: bestaande codebase analyseren en kennis opbouwen
- **Discovery Tool**: requirements ophalen en verfijnen (brownpaper + greenpaper)
- **PM Dashboard**: voortgang monitoren met drill-down
- **Plane**: werk plannen en voortgang beheren
- **MQ DevEngine**: code schrijven en testen

Geen tool doet het werk van een ander tool.

### 7. Twee doelgroepen, gescheiden werkstromen

| Rol | Ziet | Doet |
|-----|------|------|
| **Product Manager / Stakeholder** | Discovery Tool, PM Dashboard, Plane (kanban + voortgang) | Requirements sturen, voortgang monitoren, prioriteren, reviewen, goedkeuren |
| **Developer / Tech Lead** | Onboarding, Plane, MQ DevEngine, Git | Codebase onboarden, sprints starten, executie monitoren, resultaten delen |

De PM hoeft nooit in MQ DevEngine of Onboarding te werken. De developer deelt uitkomsten met de PM via Plane en het PM Dashboard.

### 8. Confidence scoring

De AI markeert items waar het onzeker over is. Onzekere requirements worden visueel gemarkeerd zodat de mens weet waar extra aandacht nodig is bij review. Dit voorkomt dat AI-hallucinaties ongemerkt de pipeline in gaan.

### 9. Twee-sporen review

- **Business review**: leesbaar overzicht in Discovery Tool of gedeelde link — PM beoordeelt inhoud
- **Technisch review**: Git PR met markdown — tech lead beoordeelt architectuur en haalbaarheid

Beide sporen moeten goedgekeurd zijn voordat items naar Plane gepusht worden.

### 10. Progressive disclosure

De Discovery Tool start breed ("Wat bouw je? Voor wie?") en laat de AI een eerste schets maken. De mens kiest waar dieper op ingegaan wordt. Niet alles in één sessie afdwingen. Sessies zijn hervatbaar over meerdere dagen.

### 11. Gefaseerd onboarden

Nieuwe klanten starten met read-only toegang tot het dashboard en groeien naar volledige CRUD naarmate ze het platform adopteren. De CRUD-modus is per klant configureerbaar (fase 1: read-only, fase 2: toevoegen + bekijken, fase 3: volledige CRUD). Dit verlaagt de instapdrempel en voorkomt dat onervaren gebruikers per ongeluk data wijzigen.

## Complete Pipeline

### Stap 1: Codebase Analyse (Onboarding)

> Bij greenpaper (nieuwbouw) wordt deze stap overgeslagen.

Onboarding analyseert een bestaande codebase en genereert een gestructureerde breakdown:

```
Bestaande codebase + requirements
         |
         v
  Onboarding AI agents scannen:
    - Welke modules/packages bestaan er?        -> Plane Modules
    - Wat zijn de grote functionele gebieden?    -> Plane Epics
    - Welke specifieke verbeteringen/features?   -> Plane Work Items
    - Welke sub-taken per work item?             -> Plane Sub-Work Items
    - Welke dependencies tussen items?           -> Plane Relations
    - IFPUG functiepunten per entity
         |
         v
  Output: Markdown bestanden in git + kennis voor Discovery Tool
    project.md
      epics/EPIC-001/epic.md
        features/FEATURE-001/feature.md
          stories/STORY-001/story.md
            tasks/TASK-001.md
```

### Stap 2: Requirements Gathering (Discovery Tool)

De Discovery Tool heeft twee modi:

**Brownpaper** (bestaande codebase): Onboarding heeft al gescand. De Discovery Tool presenteert bevindingen aan de PM ter bevestiging, documenteert de huidige staat, en interviewt over gewenste wijzigingen.

**Greenpaper** (nieuwbouw): Er is geen bestaande codebase. De Discovery Tool start blanco met documentatie en interviews.

```
Brownpaper input:                     Greenpaper input:
  - Onboarding kennis + IFPUG FP       - PM/stakeholder visie
  - Bestaande Plane backlog             - Referentie-architectuur (optioneel)
  - PM/stakeholder antwoorden           - PM/stakeholder antwoorden
         |                                      |
         v                                      v
  AI-gestuurde workflow (BMAD-stijl fasen):
    1. Visie & context ("Wat bouw je? Voor wie?")
    2. Feature discovery ("Welke functionaliteit?")
    3. Epic decompositie (clusteren in grote gebieden)
    4. Story breakdown (per feature: stories + acceptance criteria)
    5. Micro feature validatie (elke story <= 2 uur)
    6. Review + confidence scoring
         |
         v
  Output: gestructureerde hiërarchie (JSON)
    Epic -> Feature -> Story -> Task
    met prioriteiten, acceptance criteria, dependencies
```

### Stap 3: Twee-sporen Review

```
Discovery output
         |
         +---> Business review: PM keurt inhoud goed in Discovery Tool
         |
         +---> Technisch review: Git PR met markdown voor tech lead
         |
         v (beide goedgekeurd)
  Push naar Plane
```

### Stap 3b: PM Dashboard (apart component)

Het PM Dashboard is een **zelfstandig component** naast de andere tools met twee functies:

1. **Monitoring:** Aggregeert data uit Plane (hiërarchie, states), MQ DevEngine (test results), en Onboarding (IFPUG functiepunten) tot een 4-niveau drill-down overzicht.

2. **Intake portaal** (vanaf CRUD fase 2): De PM kan direct vanuit de hiërarchie nieuwe requirements, change requests en bug reports aanmaken. Items worden automatisch gerouteerd:
   - **Nieuw requirement** → Discovery Tool (brownpaper) voor decompositie → Plane
   - **Change request** → Direct naar Plane cycle → MQ DevEngine
   - **Bug report** → Direct naar Plane cycle (hoge prio) → MQ DevEngine

Elk intake item heeft een volledige audit trail (wie, wanneer, welke fase, welke acties, test results) en is traceerbaar via Plane labels en parent-relaties.

Zie [platform-overview.md](platform-overview.md) voor de volledige specificatie: drill-down niveaus, metriek, fase-tracking, CRUD-modus, intake flow, audit trail, en helpdesk connector architectuur.

### Stap 4: Sprint Planning (Plane)

Mens organiseert werk in Plane:

- Drag & drop in cycles (sprints)
- Prioriteiten aanpassen
- Deadlines zetten
- Modules toewijzen

### Stap 5: Sprint Executie (MQ DevEngine)

Plane Sync Service importeert de actieve cycle naar MQ DevEngine:

```
Plane Cycle (actief)
         |
    Sync Service pollt elke 30s
         |
         v
  MQ DevEngine Feature DB
    - Work Items -> Features
    - Priority/State/Category mapping
    - Dependencies behouden
         |
         v
  Orchestrator pakt features op
    - Coding agents implementeren (micro features, <= 2 uur)
    - Testing agents verifiëren
    - Status updates terug naar Plane
```

### Stap 6: Feedback Loop

```
Feature completion
         |
         v
  MQ DevEngine genereert:
    - Test resultaten
    - Change document (git diff + AC check)
         |
         +---> Plane work item: status update + comment met resultaten
         |
         v
  PM reviewt in PM Dashboard of Plane:
    - Goedgekeurd  -> status "Done", volgende feature
    - Afgekeurd    -> comment met feedback
                           |
                           v
                   Terug naar Discovery Tool
                   (item + feedback als context)
                           |
                           v
                   Verfijnde requirements -> Plane -> MQ DevEngine
```

### Stap 7: Doorlopende Intake (na initiële oplevering)

```
PM ziet item in Dashboard
         |
         +-- klikt [+] op epic/feature/story niveau
         |
         v
  Intake formulier: type (requirement/change/bug) + details
         |
         +--- Requirement --> Discovery Tool (brownpaper) --> Plane
         |
         +--- Change/Bug --> Direct Plane cycle --> MQ DevEngine
         |
         v
  Resultaat zichtbaar in Dashboard intake-overzicht
  met volledige audit trail per item
```

Zie [platform-overview.md](platform-overview.md) voor de volledige intake-specificatie.

## MQ DevEngine Interne Architectuur

### Backend

- **Framework:** Python/FastAPI met uvicorn
- **Database:** SQLite per project (`{project}/.mq-devengine/features.db`)
- **Settings:** SQLite registry (`~/.mq-devengine/registry.db`)
- **CLI:** Node.js entry point (`bin/mq-devengine.js` -> `lib/cli.js`)

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
mq-devEngine/
  plane_sync/
    __init__.py
    client.py           # PlaneApiClient (HTTP, auth, rate limiting, write ops)
    models.py           # Pydantic modellen voor Plane API + MQ DevEngine endpoints
    mapper.py           # Work Item <-> Feature conversie, AC parsing
    sync_service.py     # import_cycle + outbound_sync (bidirectional)
    background.py       # PlaneSyncLoop: asyncio polling per project, sprint detection
    completion.py       # Sprint completion: DoD, retrospective, git tag, release notes
    release_notes.py    # Markdown release notes generator
    webhook_handler.py  # HMAC-SHA256 verificatie + event parsing
    self_host.py        # Self-hosting: register MQ DevEngine in eigen registry
```

### Onboarding Import Module

```
mq-devEngine/
  marqed_import/
    __init__.py         # Package exports
    parser.py           # parse_marqed_tree(): directory tree -> MarQedEntity tree
    models.py           # Pydantic modellen: MarQedImportRequest/Result
    importer.py         # import_to_plane(): MarQedEntity tree -> Plane modules + work items
```

De Onboarding importer parseert markdown directory trees en creëert de corresponderende
Plane entiteiten:

| Onboarding entity | Plane entity | Rationale |
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

Naast de polling loop ondersteunt MQ DevEngine ook real-time webhooks van Plane:

- **Endpoint:** `POST /api/plane/webhooks` (exempt van localhost middleware)
- **Authenticatie:** HMAC-SHA256 verificatie met configureerbaar secret
- **Dedup:** 5-seconde cooldown per event key voorkomt dubbele verwerking
- **Events:** `issue.update` en `cycle.update` triggeren `import_cycle()` voor de actieve cycle

## Bekende Beperkingen & Geplande Fixes

### ~~Plane Sync is globaal (niet per project)~~ -- OPGELOST (Sprint 7.1)

Opgelost in Sprint 7.1. Plane sync configuratie is nu per-project. Elk project heeft eigen `plane_project_id`, `plane_active_cycle_id`, `plane_sync_enabled`, en `plane_poll_interval`. Gedeelde settings (`plane_api_url`, `plane_api_key`, `plane_workspace_slug`, `plane_webhook_secret`) blijven globaal. Zie [ADR-004](decisions/ADR-004-per-project-plane-sync.md).

### ~~Geen graceful agent shutdown~~ -- OPGELOST (Sprint 7.2)

Opgelost in Sprint 7.2. De UI biedt nu twee stop-opties:

- **Soft stop** (CircleStop knop): stuurt `SIGUSR1` naar de orchestrator. Status wordt `finishing`. De orchestrator claimt geen nieuwe features meer maar laat lopende agents hun werk afmaken. Na afronding stopt het process netjes (exit code 0 → status `stopped`).
- **Hard stop** (Square knop): stuurt `SIGTERM` → `SIGKILL` naar de hele process tree. Ongewijzigd gedrag, beschikbaar als noodknop vanuit elke state.

Status flow: `stopped → running → finishing → stopped` (graceful) of `running → stopped` (hard stop).

---

## Deployment

### Minimaal (alleen MQ DevEngine)

- MQ DevEngine server + UI
- Claude Code CLI (of Anthropic API key)
- Optioneel: OpenRouter voor multi-model support

### Volledig (MarQed.ai platform)

| Service | Vereisten | Port |
|---------|-----------|------|
| Onboarding | Python 3.12+, Docker, ChromaDB | 8000 |
| Plane | Docker Compose (PostgreSQL, Redis, MinIO) | 8080 |
| MQ DevEngine | Python 3.11+, Node.js 20+ | 5175 |
| Discovery Tool | React, FastAPI, PostgreSQL in Docker | 3000 |
| PM Dashboard | React (onderdeel Discovery Tool of standalone) | 3000 |

Alle componenten self-hosted, volledige controle over data.
