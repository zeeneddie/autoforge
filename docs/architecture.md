# AutoForge Systeemarchitectuur

## Overzicht

AutoForge is een autonoom coding platform dat software bouwt in agile sprint-cycli. Het systeem bestaat uit vier onafhankelijke componenten die samen een volledige discovery-planning-executie-feedback pipeline vormen:

| Component | Rol | Technologie | Doelgroep |
|-----------|-----|-------------|-----------|
| **Discovery Tool** | Requirements gathering, guided interviews | React/assistant-ui, FastAPI, PostgreSQL | Product Manager, Stakeholder |
| **MarQed** | Codebase analyse, onboarding kennis | Python, 11 AI agents, markdown output | Developer, Tech Lead |
| **Plane** | Planning, backlog, sprint management (SSOT) | Self-hosted, PostgreSQL, REST API | Product Manager, Developer |
| **AutoForge** | Autonome code-uitvoering, testing, delivery | Python/FastAPI, Claude Agent SDK | Developer |

```
                    MARQED                         DISCOVERY TOOL
                 (Codebase Analyse)             (Requirements Gathering)
                 +------------------+           +------------------------+
                 | Codebase scanning|           | Guided AI interviews   |
                 | Gap analyse      |           | BMAD-stijl workflows   |
                 | Kennis opbouw    |---------->| Bestaande backlog      |
                 | MD output        |  context  |   inladen + verfijnen  |
                 +------------------+           | Micro feature decomp.  |
                                                +------------------------+
                                                         |
                                                    schrijft naar
                                                         |
                                                         v
                                          +============================+
                                          ||    PLANE (SSOT)           ||
                                          || Backlog, Cycles, Modules  ||
                                          || Prioritering, Voortgang   ||
                                          +============================+
                                                    |          ^
                                              import |          | status + feedback
                                                    v          |
                                          +------------------------+
                                          |    AUTOFORGE            |
                                          |    (Executie Engine)    |
                                          |    Coding + Testing     |
                                          +------------------------+
                                                    |
                                                    | test resultaten +
                                                    | change docs
                                                    v
                                          +------------------------+
                                          |    FEEDBACK LOOP        |
                                          |    PM reviewt in Plane  |
                                          |    Approve -> Done      |
                                          |    Reject  -> Discovery |
                                          +------------------------+
```

## Ontwerpprincipes

### 1. Mens als regisseur

De AI doet het zware werk (analyseren, genereren, bouwen, testen). De mens maakt **alle GO/NO-GO beslissingen**. Geen enkel item mag automatisch van Discovery naar Plane of van Plane naar productie zonder menselijke goedkeuring.

### 2. Plane is Single Source of Truth

Plane is de enige bron van waarheid voor alle work items. De Discovery Tool is ephemeer (sessie resulteert in Plane items). MarQed is referentiemateriaal. AutoForge leest uit en schrijft terug naar Plane. Geen dubbele administratie.

### 3. Micro features: maximaal 2 uur bouwen + testen

Elke feature moet klein genoeg zijn om binnen 2 uur gebouwd en getest te worden. Dit zorgt ervoor dat:
- Gebruikers snel resultaat zien en kunnen beoordelen
- Feedback sneller terugkomt
- Er nooit lang aan het verkeerde wordt gewerkt
- Falen goedkoop is

### 4. Snel en vaak falen, kort cyclisch werken

Korte cycles, snelle feedback. Als iets niet klopt, wordt het binnen uren ontdekt — niet na dagen. De Discovery Tool decomposeert werk tot micro features. AutoForge bouwt ze snel. De PM beoordeelt snel. Afwijzingen gaan direct terug de Discovery in.

### 5. Feedback loop sluit altijd

De pipeline is cyclisch, niet lineair:
- Test resultaten → Plane work item comment
- PM reviewt → goedkeuren of afwijzen met feedback
- Afgewezen items → terug naar Discovery met context
- Verfijnde requirements → opnieuw naar Plane → opnieuw bouwen

Geen dood spoor. Elke uitkomst leidt tot een volgende actie.

### 6. Separation of duties

Elk tool heeft precies één verantwoordelijkheid:
- **Discovery Tool**: requirements ophalen en verfijnen
- **MarQed**: codebase analyseren en kennis opbouwen
- **Plane**: werk plannen en voortgang beheren
- **AutoForge**: code schrijven en testen

Geen tool doet het werk van een ander tool.

### 7. Twee doelgroepen, gescheiden werkstromen

| Rol | Ziet | Doet |
|-----|------|------|
| **Product Manager / Stakeholder** | Discovery Tool, Plane (kanban + voortgang) | Requirements sturen, prioriteren, reviewen, goedkeuren |
| **Developer / Tech Lead** | MarQed, Plane, AutoForge, Git | Analyse configureren, sprints starten, executie monitoren, resultaten delen |

De PM hoeft nooit in AutoForge of MarQed te werken. De developer deelt uitkomsten met de PM via Plane.

### 8. Confidence scoring

De AI markeert items waar het onzeker over is. Onzekere requirements worden visueel gemarkeerd zodat de mens weet waar extra aandacht nodig is bij review. Dit voorkomt dat AI-hallucinaties ongemerkt de pipeline in gaan.

### 9. Twee-sporen review

- **Business review**: leesbaar overzicht in Discovery Tool of gedeelde link — PM beoordeelt inhoud
- **Technisch review**: Git PR met markdown — tech lead beoordeelt architectuur en haalbaarheid

Beide sporen moeten goedgekeurd zijn voordat items naar Plane gepusht worden.

### 10. Progressive disclosure

De Discovery Tool start breed ("Wat bouw je? Voor wie?") en laat de AI een eerste schets maken. De mens kiest waar dieper op ingegaan wordt. Niet alles in één sessie afdwingen. Sessies zijn hervatbaar over meerdere dagen.

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
  Output: Markdown bestanden in git + kennis voor Discovery Tool
    project.md
      epics/EPIC-001/epic.md
        features/FEATURE-001/feature.md
          stories/STORY-001/story.md
            tasks/TASK-001.md
```

### Stap 2: Requirements Gathering (Discovery Tool)

De Discovery Tool leidt de PM/stakeholder door een interactief gesprek:

```
Input:
  - MarQed kennis (codebase context)
  - Bestaande Plane backlog (items om op door te werken)
  - PM/stakeholder antwoorden
         |
         v
  AI-gestuurde workflow (BMAD-stijl fasen):
    1. Visie & context ("Wat bouw je? Voor wie?")
    2. Feature discovery ("Welke functionaliteit?")
    3. Epic decomposie (clusteren in grote gebieden)
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
    - Coding agents implementeren (micro features, <= 2 uur)
    - Testing agents verifiëren
    - Status updates terug naar Plane
```

### Stap 6: Feedback Loop

```
Feature completion
         |
         v
  AutoForge genereert:
    - Test resultaten
    - Change document (git diff + AC check)
         |
         +---> Plane work item: status update + comment met resultaten
         |
         v
  PM reviewt in Plane:
    - Goedgekeurd  -> status "Done", volgende feature
    - Afgekeurd    -> comment met feedback
                           |
                           v
                   Terug naar Discovery Tool
                   (item + feedback als context)
                           |
                           v
                   Verfijnde requirements -> Plane -> AutoForge
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
