# MarQed.ai Roadmap v2

> Bijgewerkt: 2026-02-12

## Strategische Wijziging

De oorspronkelijke roadmap plande 7 sprints om een compleet agile planning-systeem te bouwen (data model, analyse workflow, kanban boards, velocity metrics). Door integratie met **MQ Planning** (open-source PM tool) en **Onboarding** (codebase analyse) is het kern-platform in **7 sprints** opgeleverd.

Fase 2 (Sprint 8+) bouwt de **Discovery-laag** en het **PM Dashboard**: een grafische, interactieve requirements-workflow die BMAD vervangt, plus een hiërarchisch overzicht voor product managers en stakeholders. Samen vormen deze componenten het **MarQed.ai platform**.

Zie [ADR-001](decisions/ADR-001-plane-integration.md) voor de rationale.

## Pipeline Overzicht

```
Onboarding (Analyse) -> Discovery Tool (Requirements) -> MQ Planning (Planning) -> MQ DevEngine (Executie)
                                                                  |
                                                             PM Dashboard (Monitoring)
                                                           [data uit MQ Planning + MQ DevEngine + Onboarding]
```

Onboarding levert codebase-kennis (kwaliteit, performance, security, IFPUG FP) die de Discovery-workflow voedt. Het PM Dashboard aggregeert data uit MQ Planning, MQ DevEngine en Onboarding. Zie [platform-overview.md](platform-overview.md) voor het volledige platformdiagram en [architecture.md](architecture.md) voor de architectuur.

---

## Sprint 1: Multi-Model Support -- DONE

> Afgerond: 2026-02-06 | Commit: `d0a3e83`

Per agent-type model selectie met OpenRouter support.

| # | Item | Status |
|---|---|---|
| 1.1 | Per agent-type model configuratie in registry/settings | done |
| 1.2 | API schema's uitbreiden (model per agent-type in start request) | done |
| 1.3 | Process manager: juiste model doorgeven per agent subprocess | done |
| 1.4 | Orchestrator: per-type model routing naar coding/testing/initializer | done |
| 1.5 | UI: model selectie per agent-type op settings pagina | done |
| 1.6 | Model validatie gerelaxed: accepteert OpenRouter/Ollama/GLM model IDs | done |
| 1.7 | Documentatie: OpenRouter setup in README | done |

---

## Sprint 2: MQ Planning Integratie - Inbound Sync -- DONE

> Afgerond: 2026-02-10 | Commit: `cbd5953`

Work items uit MQ Planning importeren als MQ DevEngine Features.

| # | Item | Status |
|---|---|---|
| 2.1 | PlanningApiClient met auth + rate limiting (`planning_sync/client.py`) | done |
| 2.2 | Pydantic modellen voor MQ Planning API entities (`planning_sync/models.py`) | done |
| 2.3 | Feature tabel migratie: planning_work_item_id, planning_synced_at, planning_updated_at | done |
| 2.4 | DataMapper: MQ Planning WorkItem -> MQ DevEngine Feature (`planning_sync/mapper.py`) | done |
| 2.5 | Import endpoint: `POST /api/planning/import-cycle` | done |
| 2.6 | API endpoints: config, test-connection, cycles | done |
| 2.7 | Settings UI: MQ Planning connectie configuratie in SettingsModal | done |
| 2.8 | Test connection + cycles ophalen in UI | done |

**Acceptatiecriteria:**
1. Maak een Cycle in MQ Planning met 3-5 work items
2. Configureer MQ Planning API credentials in MQ DevEngine settings
3. Klik "Import Sprint" in MQ DevEngine UI
4. Features verschijnen in MQ DevEngine's feature DB met juiste priority/category/dependencies
5. Start de agent -- features worden opgepakt en geimplementeerd

**Technische details:** Zie [planning-sync/api-design.md](planning-sync/api-design.md)

---

## Sprint 3: MQ Planning Integratie - Bidirectionele Sync -- DONE

> Afgerond: 2026-02-10

Bidirectionele status sync: MQ DevEngine feature status wordt automatisch naar MQ Planning gepusht, en MQ Planning wijzigingen worden opgehaald via een achtergrond polling loop.

| # | Item | Status |
|---|---|---|
| 3.1 | Outbound sync: Feature status -> MQ Planning work item state | done |
| 3.2 | Echo prevention via status hash + timestamp vergelijking | done |
| 3.3 | Background polling loop (configurable interval) | done |
| 3.4 | Mid-sprint sync (nieuwe/gewijzigde/verwijderde items) | done |
| 3.5 | MQ Planning sync status in MQ DevEngine UI | done |
| 3.6 | Optionele webhook handler met HMAC-SHA256 verificatie | done (Sprint 5) |
| 3.7 | Change document generatie (git diff + AI summary) | done (Sprint 4) |

**Acceptatiecriteria:**
1. MQ Planning work items gaan automatisch naar "started" als MQ DevEngine ze oppakt
2. MQ Planning work items gaan naar "completed" als Features passing worden
3. Edit een work item in MQ Planning mid-sprint -- wijziging komt door in MQ DevEngine
4. Echo prevention: MQ DevEngine's eigen updates triggeren geen onnodige re-sync

**Technische details:** Zie [decisions/ADR-003-data-mapping.md](decisions/ADR-003-data-mapping.md)

---

## Sprint 4: DoD & Sprint Completion -- DONE

> Afgerond: 2026-02-10

Structured sprint completion met DoD verificatie, retrospective naar MQ Planning, en git tagging.

| # | Item | Status |
|---|---|---|
| 4.1 | Acceptance criteria uit MQ Planning work item description parsen | done |
| 4.2 | DoD checks per feature (acceptance criteria + regression) | done |
| 4.3 | Sprint completion detectie (alle features passing) | done |
| 4.4 | Retrospective data genereren (schrijf naar MQ Planning als cycle comment) | done |
| 4.5 | Git tag per sprint | done |
| 3.7 | Change document generatie (git log summary in retrospective) | done |

**Acceptatiecriteria:**
1. Import een MQ Planning work item met "Acceptance Criteria:" sectie -- steps worden correct geextraheerd
2. Importeer cycle, markeer alle features als passing -- sync status toont `sprint_complete: true`
3. Klik "Complete Sprint" in UI -- comments op MQ Planning work items, git tag aangemaakt, resultaat in UI
4. Change log: git log sinds laatste tag zit in retrospective
5. Idempotentie: dubbel klikken maakt geen duplicate tags/comments

---

## Sprint 5: Continuous Delivery -- DONE

> Afgerond: 2026-02-10

Test history tracking, release notes generatie, en real-time MQ Planning webhooks.

| # | Item | Status |
|---|---|---|
| 5.2 | Regression test reporting: TestRun DB model, recording in orchestrator, test-report API | done |
| 5.1 | Release notes generatie uit voltooide features (markdown, per sprint) | done |
| 3.6 | MQ Planning webhooks: HMAC-SHA256 verificatie, event dedup, issue/cycle routing | done |
| 5.3 | Self-hosting: MQ DevEngine eigen backlog in MQ Planning | done (Sprint 6) |
| 5.4 | Onboarding -> MQ Planning importer (markdown -> MQ Planning entities) | done (Sprint 6) |

**Acceptatiecriteria:**
1. Start agents met `testing_agent_ratio >= 1`, wacht op completion, `GET /api/planning/test-report` -> runs geregistreerd
2. Sync status bevat `total_test_runs` en `overall_pass_rate`
3. Complete sprint met alle features passing -> `releases/sprint-{name}.md` bevat features, test tabel, change log
4. `curl` met geldige HMAC -> 200, ongeldige -> 403, webhook count stijgt in sync status
5. UI: webhook secret veld, test stats in sprint sectie, release notes pad na completion

**Technische details:**
- `TestRun` DB model: per-feature per-agent test resultaten met batch info en timestamps
- Orchestrator `running_testing_agents` uitgebreid naar 4-tuple: `(fid, proc, batch, start_time)`
- `_record_test_runs()` helper schrijft na elke agent completion (testing + coding)
- Release notes: `planning_sync/release_notes.py` met features per categorie, test tabel, change log
- Webhooks: `POST /api/planning/webhooks` met HMAC-SHA256, 5s event dedup, routes naar `import_cycle()`
- Webhook endpoint exempt van localhost middleware (HMAC is de auth)
- Sprint stats uitgebreid met `total_test_runs`, `overall_pass_rate`

---

## Sprint 6: Self-Hosting + Onboarding Importer -- DONE

> Afgerond: 2026-02-10

Self-hosting setup en Onboarding-to-MQ Planning import pipeline.

| # | Item | Status |
|---|---|---|
| 6.1 | Fix `background.py` registry import bug (`get_all_projects` -> `list_registered_projects`) | done |
| 6.2 | Self-hosting setup: `POST /api/planning/self-host-setup` registreert MQ DevEngine in eigen registry | done |
| 6.3 | PlanningApiClient write operations: `create_work_item`, `create_module`, `add_work_items_to_module`, `add_work_items_to_cycle` | done |
| 6.4 | Onboarding markdown parser: `marqed_import/parser.py` met `parse_marqed_tree()` | done |
| 6.5 | Onboarding-to-MQ Planning importer: `POST /api/planning/marqed-import` creates modules + work items in MQ Planning | done |
| 6.6 | Documentatie update: roadmap, architecture, API design | done |

**Acceptatiecriteria:**
1. `POST /api/planning/self-host-setup` registreert "mq-devengine" in registry (idempotent)
2. Onboarding parser: 1 epic + 2 features + 3 stories -> correct nested entity tree
3. Onboarding import: creates 1 module + 5 work items in MQ Planning met correcte parent relaties
4. Items in juiste module, optioneel in cycle
5. Fouten per item stoppen niet de gehele import
6. Server start zonder errors, alle endpoints bereikbaar

---

## Sprint 7: Analytics Dashboard -- DONE

> Afgerond: 2026-02-11

Analytics view als derde view-modus naast Kanban en Dependency Graph. Test report visualisatie, sprint metrics, en release notes viewer.

| # | Item | Status |
|---|---|---|
| 7.1 | Backend: 5 Pydantic modellen + 3 nieuwe endpoints (test-history, release-notes, release-notes/content), test-report uitgebreid met `all_features` param | done |
| 7.2 | Frontend: 5 TypeScript interfaces, 3 API functies, 3 React Query hooks | done |
| 7.3 | ViewToggle uitbreiding met `analytics` mode + `BarChart3` icon, App.tsx wiring + `I` keyboard shortcut | done |
| 7.4 | AnalyticsDashboard container met 3 tabs (Test Report, Sprint Metrics, Release Notes) | done |
| 7.5 | TestReportPanel: summary cards, feature tabel met pass rate bars, expandable heatmap (groen/rood cellen) | done |
| 7.6 | SprintMetricsPanel: sprint voortgang, test activiteit, feature velocity, sync status | done |
| 7.7 | ReleaseNotesViewer: twee-paneel layout, ingebouwde markdown renderer (geen externe deps) | done |

**Acceptatiecriteria:**
1. Klik Analytics in ViewToggle -> dashboard met 3 tabs
2. Test Report tab: summary cards, feature tabel, klik feature voor heatmap
3. Sprint Metrics tab: voortgang cards met data uit sync status + test report
4. Release Notes tab: bestandslijst links, inhoud rechts met markdown rendering
5. Keyboard shortcut `I` schakelt naar/van analytics view
6. Lege staten: correcte meldingen bij ontbreken van test data of release notes

**Technische details:**
- Backend: `TestRunDetail`, `TestHistoryResponse`, `ReleaseNotesItem`, `ReleaseNotesList`, `ReleaseNotesContent` modellen
- Path traversal bescherming op release-notes/content endpoint
- Frontend: pure Tailwind heatmap (geen chart library), ingebouwde markdown renderer
- 4 nieuwe componenten, 7 gewijzigde bestanden

---

## Sprint 7.1: Per-Project MQ Planning Sync -- DONE

> Afgerond: 2026-02-12 | Commit: `0755248`

Per-project MQ Planning sync configuratie. Voorkomt cross-project data lekkage bij meerdere projecten.

| # | Item | Status |
|---|---|---|
| 7.1.1 | Registry keys uitbreiden: `planning_*` settings met `:project_name` suffix + backward-compat fallback | done |
| 7.1.2 | `PlanningSyncLoop._sync_iteration()` itereert per project, leest per-project config | done |
| 7.1.3 | API endpoints: `GET/POST /api/planning/config?project_name=X` + alle sync endpoints | done |
| 7.1.4 | UI: MQ Planning config per geselecteerd project in SettingsModal | done |
| 7.1.5 | Migratie: globale `planning_*` keys → eerste geregistreerde project bij startup | done |

**Acceptatiecriteria:**
1. `klaverjas_app` en `mq-discovery` draaien tegelijk met elk hun eigen MQ Planning cycle
2. Start sync → features verschijnen alleen in het juiste project
3. Disable sync voor project A → project B sync draait door ongestoord
4. Legacy single-project setup werkt zonder configuratie-wijzigingen
5. UI toont per-project MQ Planning configuratie

**Technische details:**
- `registry.py`: `get_planning_setting()`, `set_planning_setting()`, `migrate_global_planning_settings()`
- Per-project keys: `planning_project_id`, `planning_active_cycle_id`, `planning_sync_enabled`, `planning_poll_interval`
- Shared keys: `planning_api_url`, `planning_api_key`, `planning_workspace_slug`, `planning_webhook_secret`
- Registry key pattern: `{key}:{project_name}` met fallback naar global
- Sync loop: `_get_project_config(project_name)` + `_per_project_status` dict
- Webhook handler: iterates projects, imports only matching cycles
- 12 bestanden gewijzigd, 376 insertions, 265 deletions
- Zie [ADR-004](decisions/ADR-004-per-project-plane-sync.md)

---

## Sprint 7.2: Graceful Agent Shutdown (Soft Stop) -- DONE

> Afgerond: 2026-02-12 | Commit: `e969c9f`

Graceful agent shutdown: agents ronden lopend werk af in plaats van hard gekilld te worden. Voorkomt half-geschreven code en abandoned features.

| # | Item | Status |
|---|---|---|
| 7.2.1 | Orchestrator: `SIGUSR1` handler die `_shutdown_requested=True` zet maar `is_running=True` houdt | done |
| 7.2.2 | Orchestrator main loop: bestaande logica claimt geen nieuwe features bij `_shutdown_requested`, wacht tot alle agents klaar zijn | done |
| 7.2.3 | Process manager: `soft_stop()` methode die `SIGUSR1` stuurt + `finishing` status, healthcheck behandelt exit code 0 als `stopped` | done |
| 7.2.4 | API endpoint: `POST /api/projects/{name}/agent/soft-stop` + `finishing` status in AgentStatus schema | done |
| 7.2.5 | UI: twee-knop layout (soft stop + hard stop) bij running, "Finishing..." badge met spinner bij finishing state | done |

**Acceptatiecriteria:**
1. Klik soft stop (CircleStop) → agents claimen geen nieuwe features meer
2. Lopende agents maken hun huidige feature af (pass of fail)
3. Zodra alle agents klaar zijn → orchestrator stopt, status wordt "stopped"
4. UI toont "Finishing..." badge met spinner tijdens afronding
5. Hard stop (Square) werkt nog steeds als noodknop vanuit elke state
6. Features eindigen op `passes` of `pending` — nooit op `in_progress` na soft stop

**Technische details:**
- Status flow: `stopped → running → finishing → stopped` (graceful) of `running → stopped` (hard stop)
- SIGUSR1 handler zet alleen `_shutdown_requested=True`, NIET `is_running=False` — main loop draait door
- `process_manager.py`: `soft_stop()` stuurt `signal.SIGUSR1`, `healthcheck()` + `_stream_output()` behandelen exit code 0 als `stopped` (niet `crashed`)
- Frontend: `useSoftStopAgent()` hook, `softStopAgent()` API functie, `CircleStop` icoon
- 8 bestanden gewijzigd, 116 insertions, 23 deletions

---

## Sprint 8a: Discovery Tool Foundation -- PLANNED

> Doel: Project opzet en kern-backend voor de Discovery Tool. Database, MQ Planning integratie, Claude API, en het gefaseerde prompt systeem.

| # | Item | Status |
|---|---|---|
| 8a.1 | Project setup: React + assistant-ui + shadcn/ui frontend, FastAPI backend, PostgreSQL in Docker | planned |
| 8a.2 | Database schema: sessions, entities, AC, messages, onboarding_context tabellen + Alembic migrations | planned |
| 8a.3 | MQ Planning SDK integratie: lees modules, work items, sub-work items, cycles uit geconfigureerd project | planned |
| 8a.4 | Claude API backend: SDK setup, streaming endpoint, token tracking | planned |
| 8a.5 | Phased prompt system: context gathering, scope, decomposition, refinement, validation, export | planned |
| 8a.6 | Structured output schema: Claude `strict: true` voor Epic/Feature/Story generatie | planned |

**Acceptatiecriteria:**
1. `npm run dev` serves frontend, `uvicorn` serves backend, PostgreSQL runs in Docker
2. Alembic migrations create all 5 tables
3. MQ Planning SDK reads modules, work items, and cycles from configured project
4. Claude API streaming endpoint delivers tokens via SSE
5. Phase 1 prompt gathers project context through conversational questions
6. Phases 2-6 prompts produce increasingly refined entity hierarchy
7. Brownpaper mode loads Onboarding output as initial context
8. Greenpaper mode starts blank with open-ended questions
9. Structured output returns validated Epic/Feature/Story JSON
10. Token usage tracked per message and per session

---

## Sprint 8b: Discovery Tool Completion -- PLANNED

> Doel: UI-laag, validatie, confidence scoring, MQ Planning write-back, en multi-sessie support.

| # | Item | Status |
|---|---|---|
| 8b.1 | Chat interface: assistant-ui setup, message streaming display, user input handling | planned |
| 8b.2 | Hierarchy tree view: tree component, live SSE updates, expand/collapse | planned |
| 8b.3 | Split-screen layout: resizable panels, responsive, keyboard shortcuts | planned |
| 8b.4 | Wizard progress indicator: phases 1-6 visualization, current phase highlight | planned |
| 8b.5 | Micro feature validation: AI decomposition check -- max 2hr per story | planned |
| 8b.6 | Confidence scoring: uncertain items highlighted orange/red | planned |
| 8b.7 | Push to MQ Planning: write modules, work items, sub-work items, cycle assignment | planned |
| 8b.8 | Multi-session support: PostgreSQL persistence, resume sessions | planned |

**Acceptatiecriteria:**
1. Chat messages stream in real-time via assistant-ui components
2. Hierarchy tree grows live as AI generates entities
3. Split-screen with resizable drag handle, responsive mobile fallback
4. Phase indicator shows current phase with progress visualization
5. AI flags stories estimated >2 hours for further decomposition
6. Low-confidence entities shown with visual indicator (orange/red badges)
7. "Push to MQ Planning" creates modules, work items, sub-items in correct hierarchy
8. Sessions persist across browser refreshes and server restarts
9. Non-technical PM can complete full requirements workflow without CLI
10. Keyboard shortcuts: Enter send, Shift+Enter newline, Cmd+S manual save

---

## Sprint 8c: PM Dashboard -- PLANNED

> Doel: Hiërarchisch PM Dashboard met 4-niveau drill-down, aggregatie uit meerdere bronnen, en configureerbare CRUD-rechten.

| # | Item | Status |
|---|---|---|
| 8c.1 | Aggregation API: data from MQ Planning hierarchy + MQ DevEngine test results + Onboarding IFPUG FP | planned |
| 8c.2 | Dashboard UI: 4-level drill-down (Application > Epic > Feature > Story) | planned |
| 8c.3 | Breadcrumb navigation across all hierarchy levels | planned |
| 8c.4 | Metrics per level: children count, FP sum, tests per category, phase status | planned |
| 8c.5 | Configurable CRUD mode: read-only fase 1, add+view fase 2, full CRUD fase 3 | planned |

**Acceptatiecriteria:**
1. Aggregation API combines data from MQ Planning, MQ DevEngine, and Onboarding sources
2. Dashboard shows Application level with summary of all epics, features, stories
3. Click epic drills down to show features with their metrics
4. Click feature drills down to show stories with individual metrics
5. Breadcrumb navigation works correctly at all 4 levels
6. Each level displays: children count, FP (IFPUG), tests per category, phase status
7. CRUD mode configurable per tenant (default: read-only)
8. Phase 2 CRUD allows adding new items via inline forms
9. Phase 3 CRUD enables full edit and delete operations
10. Dashboard loads within 2 seconds for projects with 100+ entities

---

## Sprint 9: Platform Architecture -- PLANNED

> Doel: Multi-tenancy foundations, team profiles, and deployment infrastructure.

| # | Item | Status |
|---|---|---|
| 9.1 | Multi-tenancy database: schema-per-tenant PostgreSQL, tenant context middleware | planned |
| 9.2 | Tenant management API: create/list/configure tenants, admin endpoints | planned |
| 9.3 | Per-application team profiles: AI model selection per app, prompt context per stack | planned |
| 9.4 | Authentication & authorization: tenant-scoped login, role-based access (viewer/editor/admin) | planned |
| 9.5 | Deployment automation: npm package, Docker Compose for MQ Planning, setup CLI | planned |
| 9.6 | p920 production validation: fresh install test, reproducibility check | planned |

**Acceptatiecriteria:**
1. Each tenant gets isolated PostgreSQL schema, no cross-tenant data access
2. Tenant admin can create/configure tenants and assign users
3. Team profiles specify AI models and prompt context per application
4. Role-based access: viewer (read-only), editor (intake + modify), admin (full CRUD + team management)
5. `npm install -g mq-devengine-ai` + `mq-devengine config` sets up a working instance
6. MQ Planning Docker Compose starts with correct configuration
7. p920 production server runs complete pipeline from scratch
8. Dev and prod environments are fully independent

---

## Sprint 10: Intake & Traceerbaarheid -- PLANNED

> Doel: PM kan requirements, changes en bugs invoeren via het PM Dashboard, met volledige traceerbaarheid en automatische routing.

Het PM Dashboard wordt het **intake-portaal** voor alle doorlopende wijzigingen op een bestaande applicatie. De PM navigeert naar het juiste niveau in de hiërarchie (epic/feature/story), klikt [+], en voert een nieuw item in. Het systeem routeert automatisch op basis van type.

Zie [platform-overview.md](platform-overview.md) voor de volledige intake-specificatie.

| # | Item | Status |
|---|---|---|
| 10.1 | Intake formulier UI: type selectie (requirement / change / bug), titel, omschrijving, prioriteit, automatische koppeling aan parent item. Na formulier: AI FP-inschatting met budget-indicator (maandbudget, verbruikt, beschikbaar) en PM review stap (aanpassen, bevestigen, annuleren) | planned |
| 10.2 | Intake API: MQ Planning work items aanmaken met type labels (`intake:bug`, `intake:change`, `intake:requirement`), parent relatie, bron metadata (`source:pm-dashboard`, PM naam, timestamp) | planned |
| 10.3 | Intake routing: requirements → Discovery Tool (brownpaper) voor decompositie; changes en bugs → direct naar MQ Planning cycle | planned |
| 10.4 | Audit trail: volledige event history per intake item als MQ Planning work item comments (INTAKE → PLAN → BUILD → TEST → REVIEW → DONE) | planned |
| 10.5 | Intake overzicht panel: lijst van alle intake items met status, type, prioriteit, FP, gekoppeld item, en laatste actie -- naast de bestaande hiërarchie-view. Inclusief FP-verbruik tracking per periode. | planned |
| 10.6 | Prioriteit-escalatie: critical bugs gaan voor in de huidige cycle; low-prio requirements naar backlog | planned |
| 10.7 | Intake metriek: aantal open/actief/afgerond per type, gemiddelde doorlooptijd per type, in sprint metrics | planned |
| 10.8 | Helpdesk connector architectuur: API spec + adapter-patroon voor externe ITSM-integratie (design document, implementatie later) | planned |
| 10.9 | FP-estimatie engine: AI-inschatting op basis van beschrijving-analyse (NLP), historische data (gemiddelde FP vergelijkbare items), en Onboarding IFPUG data (FP van parent-item). Confidence scoring bij beperkte bronnen. Admin-override: MarQed-admins kunnen FP-inschattingen challengen en handmatig corrigeren. | planned |
| 10.10 | FP-budget dashboard: maandbudget meter (verbruikt/ingepland/beschikbaar), overschrijdingsbeveiliging (waarschuwing, blokkade, intake uitgeschakeld bij 0 FP). Integreert met FP-abonnementsmodel. | planned |

**Acceptatiecriteria:**
1. PM navigeert naar Feature "Data Export" in Dashboard, klikt [+], kiest "Bug", vult formulier in → MQ Planning work item aangemaakt met label `intake:bug` en parent relatie
2. Bug met prioriteit "High" verschijnt automatisch in actieve MQ Planning cycle
3. Nieuw requirement gaat via Discovery Tool (brownpaper) → gedecomponeerd tot micro features → terug in MQ Planning
4. Change request gaat direct naar MQ Planning, MQ DevEngine pakt op, PM ziet resultaat in intake overzicht
5. Audit trail toont volledige geschiedenis: wie, wanneer, welke fase, welke acties, test results
6. Intake overzicht filtert op type, status, en prioriteit
7. Sprint metrics tonen intake statistieken (open/actief/afgerond per type, doorlooptijd)
8. Helpdesk connector design document beschrijft adapter-patroon, gemeenschappelijke IntakeEvent interface, en mapping voor minimaal 2 ITSM-platformen (bv. ServiceNow + Zendesk)
9. PM vult intake in → ziet AI FP-inschatting + budget-impact (maandbudget, verbruikt, beschikbaar) → kan FP aanpassen → bevestigt of annuleert
10. Bij requirement intake → Discovery decomposeert → PM ziet FP-breakdown per sub-item → bevestigt voordat items naar MQ Planning gaan
11. Budget dashboard toont verbruikt/ingepland/beschikbaar FP; altijd zichtbaar in PM Dashboard
12. Overschrijdingsbeveiliging: waarschuwing bij grenswaarde, intake geblokkeerd als maandbudget op is, blokkademelding bij overschrijding
13. Admin-override: MarQed-admins kunnen elke FP-inschatting challengen, corrigeren en de gecorrigeerde waarde als definitief markeren

**Technische details:**
- CRUD fase 2 (toevoegen + bekijken) is prerequisite -- implementatie uit Sprint 8c.5
- MQ Planning labels voor type-classificatie: `intake:bug`, `intake:change`, `intake:requirement`, `source:pm-dashboard`
- Routing beslissing op client-side: requirement → redirect naar Discovery Tool met pre-filled context; change/bug → direct MQ Planning API call
- Audit trail events geschreven als MQ Planning work item comments met gestructureerd formaat (timestamp, fase, actor, actie)
- Intake overzicht: React component naast hiërarchie, met filters en sorteer-opties
- Helpdesk design: adapter-patroon met `IntakeEvent` interface, AI-classificatie voor type + item matching
- FP-estimatie: drie bronnen (beschrijving NLP, historische data, Onboarding IFPUG), confidence score, greenpaper fallback met bredere range
- FP-budget: maandelijks abonnement (25 FP basis), geen rollover, verbruikt/ingepland/beschikbaar tracking, overschrijdingsbeveiliging (3 niveaus), admin-override voor FP-correctie
- Human-in-the-loop: 2 review momenten voor requirements (intake + na decompositie), 1 voor changes/bugs (intake)

---

## Sprint 11: Feedback Loop & Knowledge Management -- PLANNED

> Doel: Sluit de feedback loop (MQ DevEngine → PM → Discovery) en bepaal waar Onboarding-kennis het beste opgeslagen en benut wordt.

De feedback loop zorgt ervoor dat test resultaten en PM-feedback terugvloeien naar de Discovery Tool. Onboarding-kennis (kwaliteit, performance, security, user journeys, IFPUG FP) moet het Discovery-proces voeden.

| # | Item | Status |
|---|---|---|
| 11.1 | Feedback loop: MQ DevEngine test resultaten + change docs als MQ Planning work item comments | planned |
| 11.2 | Feedback loop: Discovery Tool kan afgewezen MQ Planning items + feedback inladen als context voor verfijning | planned |
| 11.3 | Feedback loop: notificatie naar PM bij feature completion (MQ Planning notificatie of email/Slack) | planned |
| 11.4 | **Analyse**: inventariseer alle kennis-artefacten die Onboarding oplevert (MD files, rapporten, metrics, IFPUG FP) | planned |
| 11.5 | **Analyse**: bepaal optimale opslaglocatie(s) -- project-level `.knowledge/` folder, MQ Planning wiki, of Discovery DB | planned |
| 11.6 | **Analyse**: bepaal hoe Discovery Tool en PM Dashboard Onboarding-kennis consumeren (context injection, RAG, of directe file reads) | planned |
| 11.7 | Implementatie: kennis-pipeline Onboarding → opslag → Discovery Tool + PM Dashboard context | planned |
| 11.8 | Finetuning: evalueer of feedback loop en kennis-integratie werkt in de praktijk, pas aan waar nodig | planned |

**Acceptatiecriteria:**
1. Feature completion in MQ DevEngine → automatisch comment op MQ Planning work item met test resultaten
2. PM kan in MQ Planning goedkeuren (Done) of afwijzen (comment met feedback)
3. Discovery Tool kan afgewezen items + feedback laden en requirements verfijnen
4. Onboarding-kennis beschikbaar in Discovery chat (bv. "je huidige auth gebruikt JWT, wil je dat uitbreiden?")
5. Geen merkbare vertraging door kennis-loading
6. Documentatie: ADR voor gekozen opslagstrategie en feedback loop ontwerp

---

## Sprint 12: Twee-Sporen Review Workflow -- PLANNED

> Doel: Implementeer business review (PM) + technisch review (Git PR) voordat Discovery output naar MQ Planning gaat.

| # | Item | Status |
|---|---|---|
| 12.1 | **Analyse**: welke review stappen zijn noodzakelijk vs. nice-to-have? | planned |
| 12.2 | **Analyse**: wie voert welke actie uit? (PM business review, tech lead Git PR review) | planned |
| 12.3 | **Analyse**: wat is user-friendly voor niet-technische PM? (Discovery UI review vs. gedeelde link vs. export) | planned |
| 12.4 | Business review: PM keurt hiërarchie goed in Discovery Tool UI (approve/reject per epic/feature) | planned |
| 12.5 | Technisch review: Discovery output exporteren als markdown in Git branch + PR creatie | planned |
| 12.6 | Na beide goedkeuringen: automatisch naar MQ Planning pushen | planned |
| 12.7 | Workflow documentatie: rolbeschrijvingen (wie doet wat wanneer) | planned |

**Acceptatiecriteria:**
1. PM kan in Discovery Tool de voorgestelde hiërarchie reviewen en goedkeuren/afwijzen
2. Tech lead ontvangt Git PR met leesbare markdown samenvatting
3. Items worden pas naar MQ Planning gepusht na beide goedkeuringen
4. Workflow is gedocumenteerd met duidelijke rolbeschrijvingen

---

## Sprint 13: War Room Dashboards -- PLANNED

> Doel: Real-time monitoring dashboards geoptimaliseerd voor meerdere schermen en war room omgevingen.

- Real-time monitoring across 4 monitors (Intake, Planning, Execution, Quality)
- WebSocket/SSE live updates, kiosk mode, dark theme optimized for TV displays

---

## Sprint 14: Supervisor Agent -- PLANNED

> Doel: Meta-agent die alle processen bewaakt, vastlopers detecteert, en management-level rapportages genereert.

- Meta-agent monitoring all processes, stuck detection, process optimization
- Management-level reporting, quality gate before delivery

---

## Vervallen Sprints (overgenomen door MQ Planning)

| Originele Sprint | Onderwerp | Reden |
|---|---|---|
| Sprint 2 (oud) | Data Model (Epic, UserStory, Sprint tabellen) | MQ Planning heeft Modules, Work Items, Cycles |
| Sprint 3 (oud) | Analyse Workflow (analyse agent, sprint planning) | Planning gebeurt in MQ Planning, analyse in Onboarding |
| Sprint 5 (oud) | Dual Kanban Board UI | MQ Planning IS het kanban board |
| Sprint 6 (oud) | Velocity & Metrics | MQ Planning heeft ingebouwde analytics |

---

## Development Protocol

### Sprint Spelregels

Elke sprint volgt dit protocol:

**1. Planning (Claude Code + gebruiker)**
- Claude Code stelt de sprint inhoud voor op basis van de roadmap
- Gebruiker keurt goed, past aan, of voegt toe
- Scope: klein genoeg dat MQ DevEngine na de sprint nog steeds draait

**2. Uitvoering**
- Kleine, gerichte wijzigingen -- een concern per commit
- Na elke wijziging: verifiëren dat MQ DevEngine nog opstart en functioneert
- Geen wijzigingen aan meerdere kernbestanden tegelijk tenzij onvermijdelijk

**3. Definition of Done per sprint**
- Alle wijzigingen gecommit en gepusht
- MQ DevEngine start op en bestaande functionaliteit werkt
- Nieuwe functionaliteit is testbaar
- Geen regressies op bestaande features

**4. Review**
- Gebruiker test de nieuwe functionaliteit
- Feedback wordt input voor de volgende sprint

### Veiligheidsprotocol

| Regel | Waarom |
|---|---|
| Git commit na elke werkende wijziging | Rollback altijd mogelijk |
| Git push na elke sprint | Remote backup, samenwerking |
| Nooit agent.py + client.py + MCP server tegelijk wijzigen | Beperkt blast radius als iets breekt |
| Nieuwe code naast bestaande code, niet eroverheen | Bestaande functionaliteit blijft werken |
| Feature flags voor grote wijzigingen | Nieuwe flow aan/uit te zetten zonder code revert |

### Hoe een sprint te starten

De gebruiker vraagt Claude Code om de volgende sprint te starten. Claude Code:

1. Leest deze roadmap en de huidige codebase
2. Presenteert de sprint items aan de gebruiker
3. Na goedkeuring: voert de items een voor een uit
4. Na elk item: commit, verifieer dat MQ DevEngine werkt
5. Na alle items: push, sprint review met gebruiker
6. Werkt de status in deze roadmap bij

**Commando:** Gebruiker zegt: _"Start sprint [nummer]"_ of _"Wat is de volgende sprint?"_
