# AutoForge Roadmap v2

> Bijgewerkt: 2026-02-12

## Strategische Wijziging

De oorspronkelijke roadmap plande 7 sprints om een compleet agile planning-systeem te bouwen (data model, analyse workflow, kanban boards, velocity metrics). Door integratie met **Plane** (open-source PM tool) en **MarQed** (codebase analyse platform) is het kern-platform in **7 sprints** opgeleverd.

Fase 2 (Sprint 8+) bouwt de **Discovery-laag**: een grafische, interactieve requirements-workflow die BMAD vervangt als front-end voor product managers en stakeholders.

Zie [ADR-001](decisions/ADR-001-plane-integration.md) voor de rationale.

## Pipeline Overzicht

```
BMAD / Discovery UI (Requirements) -> Plane (Planning) -> AutoForge (Executie) -> Testing
         ^
         |
    MarQed (Codebase Analyse & Onboarding)
```

MarQed levert codebase-kennis (kwaliteit, performance, security, user journeys) die de Discovery-workflow voedt. Zie [architecture.md](architecture.md) voor de volledige architectuur.

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

## Sprint 2: Plane Integratie - Inbound Sync -- DONE

> Afgerond: 2026-02-10 | Commit: `cbd5953`

Work items uit Plane importeren als AutoForge Features.

| # | Item | Status |
|---|---|---|
| 2.1 | PlaneApiClient met auth + rate limiting (`plane_sync/client.py`) | done |
| 2.2 | Pydantic modellen voor Plane API entities (`plane_sync/models.py`) | done |
| 2.3 | Feature tabel migratie: plane_work_item_id, plane_synced_at, plane_updated_at | done |
| 2.4 | DataMapper: Plane WorkItem -> AutoForge Feature (`plane_sync/mapper.py`) | done |
| 2.5 | Import endpoint: `POST /api/plane/import-cycle` | done |
| 2.6 | API endpoints: config, test-connection, cycles | done |
| 2.7 | Settings UI: Plane connectie configuratie in SettingsModal | done |
| 2.8 | Test connection + cycles ophalen in UI | done |

**Acceptatiecriteria:**
1. Maak een Cycle in Plane met 3-5 work items
2. Configureer Plane API credentials in AutoForge settings
3. Klik "Import Sprint" in AutoForge UI
4. Features verschijnen in AutoForge's feature DB met juiste priority/category/dependencies
5. Start de agent -- features worden opgepakt en geimplementeerd

**Technische details:** Zie [plane-sync/api-design.md](plane-sync/api-design.md)

---

## Sprint 3: Plane Integratie - Bidirectionele Sync -- DONE

> Afgerond: 2026-02-10

Bidirectionele status sync: AutoForge feature status wordt automatisch naar Plane gepusht, en Plane wijzigingen worden opgehaald via een achtergrond polling loop.

| # | Item | Status |
|---|---|---|
| 3.1 | Outbound sync: Feature status -> Plane work item state | done |
| 3.2 | Echo prevention via status hash + timestamp vergelijking | done |
| 3.3 | Background polling loop (configurable interval) | done |
| 3.4 | Mid-sprint sync (nieuwe/gewijzigde/verwijderde items) | done |
| 3.5 | Plane sync status in AutoForge UI | done |
| 3.6 | Optionele webhook handler met HMAC-SHA256 verificatie | done (Sprint 5) |
| 3.7 | Change document generatie (git diff + AI summary) | done (Sprint 4) |

**Acceptatiecriteria:**
1. Plane work items gaan automatisch naar "started" als AutoForge ze oppakt
2. Plane work items gaan naar "completed" als Features passing worden
3. Edit een work item in Plane mid-sprint -- wijziging komt door in AutoForge
4. Echo prevention: AutoForge's eigen updates triggeren geen onnodige re-sync

**Technische details:** Zie [decisions/ADR-003-data-mapping.md](decisions/ADR-003-data-mapping.md)

---

## Sprint 4: DoD & Sprint Completion -- DONE

> Afgerond: 2026-02-10

Structured sprint completion met DoD verificatie, retrospective naar Plane, en git tagging.

| # | Item | Status |
|---|---|---|
| 4.1 | Acceptance criteria uit Plane work item description parsen | done |
| 4.2 | DoD checks per feature (acceptance criteria + regression) | done |
| 4.3 | Sprint completion detectie (alle features passing) | done |
| 4.4 | Retrospective data genereren (schrijf naar Plane als cycle comment) | done |
| 4.5 | Git tag per sprint | done |
| 3.7 | Change document generatie (git log summary in retrospective) | done |

**Acceptatiecriteria:**
1. Import een Plane work item met "Acceptance Criteria:" sectie -- steps worden correct geextraheerd
2. Importeer cycle, markeer alle features als passing -- sync status toont `sprint_complete: true`
3. Klik "Complete Sprint" in UI -- comments op Plane work items, git tag aangemaakt, resultaat in UI
4. Change log: git log sinds laatste tag zit in retrospective
5. Idempotentie: dubbel klikken maakt geen duplicate tags/comments

---

## Sprint 5: Continuous Delivery -- DONE

> Afgerond: 2026-02-10

Test history tracking, release notes generatie, en real-time Plane webhooks.

| # | Item | Status |
|---|---|---|
| 5.2 | Regression test reporting: TestRun DB model, recording in orchestrator, test-report API | done |
| 5.1 | Release notes generatie uit voltooide features (markdown, per sprint) | done |
| 3.6 | Plane webhooks: HMAC-SHA256 verificatie, event dedup, issue/cycle routing | done |
| 5.3 | Self-hosting: AutoForge eigen backlog in Plane | done (Sprint 6) |
| 5.4 | MarQed -> Plane importer (markdown -> Plane entities) | done (Sprint 6) |

**Acceptatiecriteria:**
1. Start agents met `testing_agent_ratio >= 1`, wacht op completion, `GET /api/plane/test-report` -> runs geregistreerd
2. Sync status bevat `total_test_runs` en `overall_pass_rate`
3. Complete sprint met alle features passing -> `releases/sprint-{name}.md` bevat features, test tabel, change log
4. `curl` met geldige HMAC -> 200, ongeldige -> 403, webhook count stijgt in sync status
5. UI: webhook secret veld, test stats in sprint sectie, release notes pad na completion

**Technische details:**
- `TestRun` DB model: per-feature per-agent test resultaten met batch info en timestamps
- Orchestrator `running_testing_agents` uitgebreid naar 4-tuple: `(fid, proc, batch, start_time)`
- `_record_test_runs()` helper schrijft na elke agent completion (testing + coding)
- Release notes: `plane_sync/release_notes.py` met features per categorie, test tabel, change log
- Webhooks: `POST /api/plane/webhooks` met HMAC-SHA256, 5s event dedup, routes naar `import_cycle()`
- Webhook endpoint exempt van localhost middleware (HMAC is de auth)
- Sprint stats uitgebreid met `total_test_runs`, `overall_pass_rate`

---

## Sprint 6: Self-Hosting + MarQed Importer -- DONE

> Afgerond: 2026-02-10

Self-hosting setup en MarQed-to-Plane import pipeline.

| # | Item | Status |
|---|---|---|
| 6.1 | Fix `background.py` registry import bug (`get_all_projects` -> `list_registered_projects`) | done |
| 6.2 | Self-hosting setup: `POST /api/plane/self-host-setup` registreert AutoForge in eigen registry | done |
| 6.3 | PlaneApiClient write operations: `create_work_item`, `create_module`, `add_work_items_to_module`, `add_work_items_to_cycle` | done |
| 6.4 | MarQed markdown parser: `marqed_import/parser.py` met `parse_marqed_tree()` | done |
| 6.5 | MarQed-to-Plane importer: `POST /api/plane/marqed-import` creates modules + work items in Plane | done |
| 6.6 | Documentatie update: roadmap, architecture, API design | done |

**Acceptatiecriteria:**
1. `POST /api/plane/self-host-setup` registreert "autoforge" in registry (idempotent)
2. MarQed parser: 1 epic + 2 features + 3 stories -> correct nested entity tree
3. MarQed import: creates 1 module + 5 work items in Plane met correcte parent relaties
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

## Sprint 8: Discovery Tool (Standalone Project) -- PLANNED

> Doel: Standalone requirements gathering tool met grafische UI die bidirectioneel met Plane communiceert.

De Discovery Tool is een **apart project** (niet in AutoForge) dat PMs en stakeholders door een interactief requirements-gesprek leidt. Het kan bestaande Plane backlogs inladen en verfijnen, en schrijft resultaat terug naar Plane.

**Architectuurbeslissing:** geen Eververse fork (te zware Supabase-ontkoppeling, geen hiërarchie, solo maintainer). In plaats daarvan: lichtgewicht standalone tool met bewezen bouwstenen.

| # | Item | Status |
|---|---|---|
| 8.1 | Project setup: nieuw repo, React + assistant-ui + shadcn/ui frontend, FastAPI backend, PostgreSQL in Docker | planned |
| 8.2 | Plane SDK integratie: bestaande backlog inladen (modules, work items, sub-work items) | planned |
| 8.3 | AI chat backend: Claude API via FastAPI, BMAD-stijl gefaseerde prompts (visie, features, epics, stories, review) | planned |
| 8.4 | UI: split-screen -- links conversational chat (assistant-ui), rechts live hiërarchie-boom | planned |
| 8.5 | UI: wizard voortgangsindicator (fasen 1-6) + gestructureerde vraag/antwoord cards | planned |
| 8.6 | Gestructureerd output schema (Claude structured outputs, `strict: true`) voor Epic → Feature → Story → Task | planned |
| 8.7 | Micro feature validatie: AI decomposeert tot items van max 2 uur bouwen + testen | planned |
| 8.8 | Confidence scoring: AI markeert onzekere items visueel (oranje/rood) voor review-aandacht | planned |
| 8.9 | Push naar Plane: modules, work items, sub-work items, cycle assignment via Plane Python SDK | planned |
| 8.10 | Multi-sessie support: sessies opslaan in PostgreSQL, hervatten over meerdere dagen | planned |

**Tech stack:**

| Laag | Keuze | Reden |
|------|-------|-------|
| Frontend | React + assistant-ui + shadcn/ui | Bewezen chat components, onze design patterns, MIT |
| Backend | FastAPI (Python) | Claude SDK, Plane SDK, consistentie |
| Database | PostgreSQL in Docker | Sessie opslag, discovery state, alles lokaal |
| AI | Claude API | BMAD-stijl prompts als gefaseerde workflow |
| PM koppeling | Plane Python SDK (v0.2.0) | Bidirectioneel lezen/schrijven |
| Kennis | MarQed MD files (mount/read) | Codebase context voor AI |

**Acceptatiecriteria:**
1. Open Discovery UI, beantwoord 5-10 vragen over een nieuw project
2. AI genereert hiërarchie: minimaal 2 epics, 5 features, 15 stories met acceptance criteria
3. Elke story is max 2 uur te bouwen + testen (micro feature principe)
4. Hiërarchie-boom groeit live mee in rechter paneel tijdens het gesprek
5. Bestaande Plane backlog inladen en verfijnen werkt
6. Onzekere items zijn visueel gemarkeerd (confidence scoring)
7. "Push naar Plane" maakt modules, work items, sub-work items aan in correcte structuur
8. Sessie afsluiten en volgende dag hervatten werkt zonder dataverlies
9. Niet-technische gebruiker kan het proces doorlopen zonder CLI-kennis

**Later (als workflows complexer worden):** evalueer migratie van assistant-ui naar CopilotKit voor generative UI en CoAgents support.

---

## Sprint 9: Feedback Loop & Knowledge Management -- PLANNED

> Doel: Sluit de feedback loop (AutoForge → PM → Discovery) en bepaal waar MarQed-kennis het beste opgeslagen en benut wordt.

De feedback loop zorgt ervoor dat test resultaten en PM-feedback terugvloeien naar de Discovery Tool. MarQed-kennis (kwaliteit, performance, security, user journeys) moet het Discovery-proces voeden.

| # | Item | Status |
|---|---|---|
| 9.1 | Feedback loop: AutoForge test resultaten + change docs als Plane work item comments | planned |
| 9.2 | Feedback loop: Discovery Tool kan afgewezen Plane items + feedback inladen als context voor verfijning | planned |
| 9.3 | Feedback loop: notificatie naar PM bij feature completion (Plane notificatie of email/Slack) | planned |
| 9.4 | **Analyse**: inventariseer alle kennis-artefacten die MarQed en onboarding opleveren (MD files, rapporten, metrics) | planned |
| 9.5 | **Analyse**: bepaal optimale opslaglocatie(s) -- project-level `.knowledge/` folder, Plane wiki, of Discovery DB | planned |
| 9.6 | **Analyse**: bepaal hoe Discovery Tool MarQed-kennis consumeert (context injection, RAG, of directe file reads) | planned |
| 9.7 | Implementatie: kennis-pipeline MarQed → opslag → Discovery Tool context | planned |
| 9.8 | Finetuning: evalueer of feedback loop en kennis-integratie werkt in de praktijk, pas aan waar nodig | planned |

**Acceptatiecriteria:**
1. Feature completion in AutoForge -> automatisch comment op Plane work item met test resultaten
2. PM kan in Plane goedkeuren (Done) of afwijzen (comment met feedback)
3. Discovery Tool kan afgewezen items + feedback laden en requirements verfijnen
4. MarQed-kennis beschikbaar in Discovery chat (bv. "je huidige auth gebruikt JWT, wil je dat uitbreiden?")
5. Geen merkbare vertraging door kennis-loading
6. Documentatie: ADR voor gekozen opslagstrategie en feedback loop ontwerp

---

## Sprint 10: Twee-Sporen Review Workflow -- PLANNED

> Doel: Implementeer business review (PM) + technisch review (Git PR) voordat Discovery output naar Plane gaat.

| # | Item | Status |
|---|---|---|
| 10.1 | **Analyse**: welke review stappen zijn noodzakelijk vs. nice-to-have? | planned |
| 10.2 | **Analyse**: wie voert welke actie uit? (PM business review, tech lead Git PR review) | planned |
| 10.3 | **Analyse**: wat is user-friendly voor niet-technische PM? (Discovery UI review vs. gedeelde link vs. export) | planned |
| 10.4 | Business review: PM keurt hiërarchie goed in Discovery Tool UI (approve/reject per epic/feature) | planned |
| 10.5 | Technisch review: Discovery output exporteren als markdown in Git branch + PR creatie | planned |
| 10.6 | Na beide goedkeuringen: automatisch naar Plane pushen | planned |
| 10.7 | Workflow documentatie: rolbeschrijvingen (wie doet wat wanneer) | planned |

**Acceptatiecriteria:**
1. PM kan in Discovery Tool de voorgestelde hiërarchie reviewen en goedkeuren/afwijzen
2. Tech lead ontvangt Git PR met leesbare markdown samenvatting
3. Items worden pas naar Plane gepusht na beide goedkeuringen
4. Workflow is gedocumenteerd met duidelijke rolbeschrijvingen

---

## Vervallen Sprints (overgenomen door Plane)

| Originele Sprint | Onderwerp | Reden |
|---|---|---|
| Sprint 2 (oud) | Data Model (Epic, UserStory, Sprint tabellen) | Plane heeft Modules, Work Items, Cycles |
| Sprint 3 (oud) | Analyse Workflow (analyse agent, sprint planning) | Planning gebeurt in Plane, analyse in MarQed |
| Sprint 5 (oud) | Dual Kanban Board UI | Plane IS het kanban board |
| Sprint 6 (oud) | Velocity & Metrics | Plane heeft ingebouwde analytics |

---

## Development Protocol

### Sprint Spelregels

Elke sprint volgt dit protocol:

**1. Planning (Claude Code + gebruiker)**
- Claude Code stelt de sprint inhoud voor op basis van de roadmap
- Gebruiker keurt goed, past aan, of voegt toe
- Scope: klein genoeg dat AutoForge na de sprint nog steeds draait

**2. Uitvoering**
- Kleine, gerichte wijzigingen -- een concern per commit
- Na elke wijziging: verifiëren dat AutoForge nog opstart en functioneert
- Geen wijzigingen aan meerdere kernbestanden tegelijk tenzij onvermijdelijk

**3. Definition of Done per sprint**
- Alle wijzigingen gecommit en gepusht
- AutoForge start op en bestaande functionaliteit werkt
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
4. Na elk item: commit, verifieer dat AutoForge werkt
5. Na alle items: push, sprint review met gebruiker
6. Werkt de status in deze roadmap bij

**Commando:** Gebruiker zegt: _"Start sprint [nummer]"_ of _"Wat is de volgende sprint?"_
