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

## Sprint 3: Plane Integratie - Bidirectionele Sync

> Doel: Status updates heen en weer syncen, real-time.

| # | Item | Status |
|---|---|---|
| 3.1 | Outbound sync: Feature status -> Plane work item state | pending |
| 3.2 | Echo prevention via timestamp vergelijking | pending |
| 3.3 | Background polling loop (30s, auto-detect active cycle) | pending |
| 3.4 | Mid-sprint sync (nieuwe/gewijzigde/verwijderde items) | pending |
| 3.5 | Plane sync status in AutoForge UI | pending |
| 3.6 | Optionele webhook handler met HMAC-SHA256 verificatie | pending |
| 3.7 | Change document generatie (git diff + AI summary) | pending |

**Acceptatiecriteria:**
1. Plane work items gaan automatisch naar "started" als AutoForge ze oppakt
2. Plane work items gaan naar "completed" als Features passing worden
3. Edit een work item in Plane mid-sprint -- wijziging komt door in AutoForge
4. Echo prevention: AutoForge's eigen updates triggeren geen onnodige re-sync

**Technische details:** Zie [decisions/ADR-003-data-mapping.md](decisions/ADR-003-data-mapping.md)

---

## Sprint 4: DoD & Sprint Completion

> Doel: Definition of Done checks, acceptance criteria, sprint afsluiting.

| # | Item | Status |
|---|---|---|
| 4.1 | Acceptance criteria uit Plane work item description parsen | pending |
| 4.2 | DoD checks per feature (acceptance criteria + regression) | pending |
| 4.3 | Sprint completion detectie (alle features passing) | pending |
| 4.4 | Retrospective data genereren (schrijf naar Plane als cycle comment) | pending |
| 4.5 | Git tag per sprint | pending |

---

## Sprint 5: Continuous Delivery & Self-Hosting

> Doel: Release management, volledige regression, AutoForge managed zichzelf.

| # | Item | Status |
|---|---|---|
| 5.1 | Release notes generatie uit voltooide features | pending |
| 5.2 | Volledige regression suite per sprint | pending |
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
