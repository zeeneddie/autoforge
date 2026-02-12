# Sprint Lifecycle: Plane + AutoForge

## Overzicht

Een complete sprint doorloopt 7 fasen, verdeeld over drie systemen.

```
MarQed          Plane           AutoForge
  |               |               |
  | 1. Analyse    |               |
  |-------------->|               |
  |               | 2. Review     |
  |     <---------|               |
  |  (Git PR)     |               |
  |               | 3. Planning   |
  |               |               |
  |               | 4. Activatie  |
  |               |-------------->|
  |               |               | 5. Executie
  |               |<--------------|
  |               |               | 6. Sync
  |               |               |
  |               | 7. Completion |
  |               |               |
```

## Fase 1: Analyse (MarQed)

**Trigger:** Nieuwe requirements, bestaande codebase, of feature request.

**Proces:**
1. MarQed AI agents scannen de codebase
2. Requirements worden gedecomponeerd naar epics/features/stories
3. Output: markdown bestanden in git repository

**Output:**
```
epics/
  EPIC-001-auth-modernization/
    epic.md
    features/
      FEATURE-001-jwt/feature.md
      FEATURE-002-oauth/feature.md
```

**Human-in-the-loop:** Pull Request review in Git. Mens valideert, past aan, keurt goed.

## Fase 2: Import naar Plane

**Trigger:** PR gemerged (gevalideerde markdown) OF handmatige import.

**Proces:**
1. md-to-plane importer leest de markdown bestanden
2. Creëert epics, work items, sub-items in Plane via API
3. Zet relations (dependencies) en priorities

**Resultaat:** Gestructureerde backlog in Plane, klaar voor sprint planning.

## Fase 3: Sprint Planning (in Plane)

**Wie:** Mens (product owner / developer)

**Acties:**
1. Maak een nieuwe Cycle (sprint) in Plane
2. Sleep work items van backlog naar cycle
3. Prioriteer binnen de cycle
4. Wijs toe aan modules indien gewenst
5. Zet start- en einddatum

**Output:** Plane Cycle met geselecteerde work items, klaar voor uitvoering.

## Fase 4: Sprint Activatie

**Trigger:** Een van de volgende:
- Cycle `start_date` bereikt (automatisch via polling)
- Handmatige "Import Sprint" knop in AutoForge UI
- API call: `POST /api/plane/import-cycle`

**Proces:**
1. AutoForge Sync Service haalt work items op uit de actieve cycle
2. DataMapper converteert naar Features:
   - Title -> name
   - Description -> description
   - Priority -> priority (int mapping)
   - Module -> category
   - State group -> passes/in_progress
   - Parent -> dependencies
3. Features worden aangemaakt in project's feature DB
4. `plane_work_item_id` en `plane_synced_at` worden opgeslagen

**Resultaat:** Features in AutoForge DB, klaar voor de orchestrator.

## Fase 5: Sprint Executie (AutoForge)

**Wie:** AutoForge agents (coding + testing)

**Proces:**
1. Orchestrator selecteert features op basis van priority en dependencies
2. Coding agent implementeert de feature
3. Testing agent verifieert (acceptance criteria, regression tests)
4. Bij succes: `passes=true`, `in_progress=false`
5. Bij falen: `passes=false`, terug in queue

**Ongewijzigd:** De bestaande orchestrator en agents hoeven niet aangepast te worden. Ze werken met Features uit de DB, ongeacht of die uit Plane of een app_spec komen.

## Fase 6: Bidirectionele Sync (Sprint 3)

**Achtergrond:** Polling loop elke 30 seconden.

### Outbound (AutoForge -> Plane)

| Feature event | Plane actie |
|---|---|
| Agent start feature (in_progress=true) | Work Item state -> "started" |
| Feature passing (passes=true) | Work Item state -> "completed" |
| Feature failing (passes=false, was true) | Work Item state -> "unstarted" |

### Inbound (Plane -> AutoForge)

| Plane event | AutoForge actie |
|---|---|
| Work item description gewijzigd | Feature description updaten |
| Work item priority gewijzigd | Feature priority updaten |
| Nieuw work item toegevoegd aan cycle | Nieuwe Feature aanmaken |
| Work item verwijderd uit cycle | Feature markeren als "niet meer in sprint" |

### Echo Prevention

Na elke outbound push:
1. Sla Plane's `updated_at` op als `Feature.plane_updated_at`
2. Bij volgende poll: vergelijk timestamps
3. Gelijk = eigen update = skip
4. Verschillend = menselijke edit = sync

## Fase 7: Sprint Completion & Delivery

**Trigger:** Alle features in sprint passing (`sprint_complete: true` in sync status).

**Stap 1: DoD Verificatie**
- AutoForge controleert of alle Plane-gelinkte features `passes=true` hebben
- Als niet alle features passing zijn, wordt completion geweigerd met details

**Stap 2: Change Log**
- `git log --oneline` sinds de laatste git tag

**Stap 3: Retrospective naar Plane**
- Completion comment op elk work item met status + change log
- Cycle description update met retrospective samenvatting (pass rate, feature lijst)

**Stap 4: Git Tag**
- Format: `sprint/{cycle-name-lowercase-dashes}`
- Bevat tag message met pass rate

**Stap 5: Release Notes**
- Markdown document gegenereerd naar `releases/sprint-{slug}.md`
- Bevat: summary (datum, tag, pass rate), features per categorie, test results tabel, change log
- Test results tabel bevat per-feature: runs, pass/fail count, rate, last result
- Data komt uit het `TestRun` model (geregistreerd door de orchestrator)

**Stap 6: Registry Flag**
- `plane_sprint_completed_{cycle_id}=true` in registry

**Output:**
- Git tag op HEAD
- Release notes in `releases/` directory
- Retrospective comments op Plane work items
- Cycle description update in Plane

## Test History (Sprint 5)

De orchestrator registreert `TestRun` records na elke agent completion:

| Agent type | Wanneer | Data |
|---|---|---|
| Testing agent | Na elke batch completion | feature_ids, passed state, batch info, timing, return code |
| Coding agent | Na elke feature completion | feature_ids, passed state, return code |

**Aggregatie:**
- `GET /api/plane/test-report?project_name=X` geeft per-feature en totaal overzicht
- Sprint stats in sync status bevatten `total_test_runs` en `overall_pass_rate`
- Release notes bevatten een test results tabel

## Webhooks (Sprint 5)

Naast de 30-seconde polling loop ondersteunt AutoForge ook real-time webhooks:

- Configureer webhook secret in AutoForge settings (optioneel maar aanbevolen)
- Configureer in Plane: webhook URL = `{autoforge-url}/api/plane/webhooks`
- Events (`issue.update`, `cycle.update`) triggeren directe re-import van de actieve cycle
- Event dedup voorkomt dubbele verwerking (5s cooldown per event key)
- Webhook count en timestamp zichtbaar in sync status UI

## Foutscenario's

### Plane niet bereikbaar tijdens executie

- AutoForge werkt gewoon door (features zijn lokaal in SQLite)
- Outbound sync queue: status updates worden gebufferd
- Bij reconnect: batch push van alle gemiste updates

### Feature faalt herhaaldelijk

- Feature blijft `passes=false` in AutoForge
- Work item in Plane blijft op "started" (niet terug naar "unstarted" tot handmatige interventie)
- Na X pogingen: log warning, ga door met andere features

### Mid-sprint wijzigingen in Plane

- Mens voegt work item toe aan cycle in Plane
- Volgende poll detecteert nieuw item -> importeert als Feature
- Mens verwijdert work item uit cycle -> Feature wordt gemarkeerd (niet verwijderd)
- Mens wijzigt priority -> Feature priority wordt bijgewerkt

### Conflicterende edits

- AutoForge en mens wijzigen tegelijk
- **Regel:** Plane (mens) wint altijd
- AutoForge detecteert via timestamp dat er een menselijke edit was
- Menselijke wijziging wordt overgenomen, AutoForge's wijziging wordt overschreven

### Cross-project data lekkage (globale sync)

- **Status:** Workaround actief, fix gepland in Sprint 7.1
- Plane sync configuratie is globaal — bij meerdere projecten importeert de sync loop work items naar alle projecten
- **Workaround:** Disable sync bij meerdere projecten, gebruik handmatige import per project
- **Oplossing:** Per-project sync met `:project_name` suffix op registry keys
- Zie [ADR-004](../decisions/ADR-004-per-project-plane-sync.md)
