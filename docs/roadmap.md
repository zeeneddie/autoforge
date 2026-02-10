# AutoForge Roadmap v2

> Bijgewerkt: 2026-02-10

## Strategische Wijziging

De oorspronkelijke roadmap plande 7 sprints om een compleet agile planning-systeem te bouwen (data model, analyse workflow, kanban boards, velocity metrics). Door integratie met **Plane** (open-source PM tool) en **MarQed** (codebase analyse platform) wordt dit teruggebracht naar **5 sprints**.

Zie [ADR-001](decisions/ADR-001-plane-integration.md) voor de rationale.

## Pipeline Overzicht

```
MarQed (Analyse) -> Git PR (Review) -> Plane (Planning) -> AutoForge (Executie)
```

Zie [architecture.md](architecture.md) voor de volledige architectuur.

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
| 3.7 | Change document generatie (git diff + AI summary) | deferred (Sprint 4) |

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
| 5.3 | Self-hosting: AutoForge eigen backlog in Plane | deferred |
| 5.4 | MarQed -> Plane importer (markdown -> Plane entities) | deferred |

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

## Toekomstige Items

| # | Item | Status |
|---|---|---|
| 5.3 | Self-hosting: AutoForge eigen backlog in Plane | pending |
| 5.4 | MarQed -> Plane importer (markdown -> Plane entities) | pending |

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
