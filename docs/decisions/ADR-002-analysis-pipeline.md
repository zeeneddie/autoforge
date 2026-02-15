# ADR-002: Analyse Pipeline - Waar Welke Stap Plaatsvindt

**Status:** Geaccepteerd
**Datum:** 2026-02-10
**Beslisser:** Eddie

## Context

Bij het opnemen van bestaande applicaties in het MQ DevEngine ecosysteem moeten we bepalen waar elke stap in de pipeline plaatsvindt:

1. **Analyse** - Codebase scannen, requirements decomponeren naar epics/features/stories
2. **Review** - Mens valideert en past aan
3. **Planning** - Organiseren in sprints, prioriteren
4. **Executie** - Code schrijven en testen
5. **Documentatie** - Vastleggen wat er is gewijzigd

## Beslissing

Elke stap heeft een duidelijke eigenaar:

| Stap | Tool | Rationale |
|------|------|-----------|
| **Analyse** | MarQed | Gebouwd voor codebase analyse, 11 AI agents, gestructureerde markdown output |
| **Review** | Git PR | Markdown is diffable, inline review comments, approval workflow, audit trail |
| **Planning** | Plane | Gebouwd voor PM, drag & drop, cycles, burndown charts |
| **Executie** | MQ DevEngine | Gebouwd voor autonome code-uitvoering, parallel agents |
| **Documentatie** | MQ DevEngine -> MarQed + Plane | MQ DevEngine heeft de git diffs, pusht change docs naar beide systemen |

## Waarom MarQed voor Analyse (niet MQ DevEngine of Plane)

### MarQed is analyse-first

- 11 gespecialiseerde AI agents voor code scanning
- Legacy quickscan (15 minuten, Go/No-Go)
- CWE security scanner
- Stability analysis
- Function Point estimation (IFPUG/NESMA)

### MQ DevEngine is execution-first

- MQ DevEngine's agents (initializer, coding, testing) zijn gebouwd voor uitvoering
- De initializer agent creëert features uit een app_spec, maar doet geen diepe codebase-analyse
- Analyse toevoegen aan MQ DevEngine zou scope creep zijn

### Plane heeft geen analyse-capability

- Plane is puur planning en tracking
- Geen codebase scanning of AI-gestuurde decompositie

## Waarom Git PR voor Review (niet direct in Plane)

### Markdown is het ideale review-format

```
# EPIC-001 | Authentication Modernization

**Priority:** HIGH
**Status:** PLANNED

## Features
- FEATURE-001: Replace session-based auth with JWT
- FEATURE-002: Add OAuth2 providers (Google, GitHub)
- FEATURE-003: Implement MFA
```

- **Diffable:** Exact zien wat de AI voorstelt vs. wat er al was
- **Reviewable:** Inline comments op specifieke regels
- **Versionable:** Wijzigingshistorie in git
- **Approachable:** Iedereen kan markdown lezen

### Plane review is complementair, niet primair

- In Plane kun je herschikken, reprioriteren, toewijzen
- Maar de inhoudelijke review (is deze epic correct? mist er een feature?) is beter in markdown/git

## Analyse Output Format

MarQed genereert de volgende directorystructuur:

```
project/
  project.md                              # Project overzicht
  epics/
    EPIC-001-authentication/
      epic.md                             # Epic beschrijving, goals, acceptance criteria
      features/
        FEATURE-001-jwt-migration/
          feature.md                      # Feature beschrijving, story points
          stories/
            STORY-001-token-service/
              story.md                    # User story, acceptance criteria, DoD
              tasks/
                TASK-001.md               # Concrete implementatie-taak
                TASK-002.md
```

### Mapping naar Plane

| MarQed | Plane Entity | Relatie |
|--------|-------------|---------|
| project.md | Project | 1:1 |
| epic.md | Epic | Title, priority, goals -> description |
| feature.md | Work Item (parent: Epic) | Title, description, story points |
| story.md | Sub-Work Item (parent: Work Item) | User story, acceptance criteria |
| TASK-*.md | Sub-Work Item of checklist item | Concrete taken |
| Dependencies (Blocks/Depends On) | Relations (blocked-by) | Direct |
| Priority emoji | Priority level | Mapping tabel |
| Status | State group | Mapping tabel |

## Change Document (Post-Executie)

Na elke voltooide feature genereert MQ DevEngine een change document:

```markdown
# Change Document: FEATURE-001 - JWT Migration

## Samenvatting
Session-based authenticatie vervangen door JWT tokens met refresh flow.

## Gewijzigde Bestanden
| Bestand | Wijziging | Regels |
|---------|-----------|--------|
| auth/login.py | Modified | 45-62 |
| auth/jwt_service.py | New | 1-89 |
| auth/middleware.py | Modified | 12-18, 34-41 |
| tests/test_auth.py | Added tests | 20-67 |
| requirements.txt | Added dependency | 12 |

## Acceptance Criteria Status
- [x] JWT tokens worden uitgegeven bij login
- [x] Refresh tokens werken correct
- [x] Oude session-based auth is verwijderd
- [x] Alle bestaande tests passen nog

## Git
- Commit: a1b2c3d
- Diff: +214 lines, -43 lines
```

Dit document wordt:
1. Opgeslagen als `change-doc.md` in de MarQed story directory
2. Gepusht als comment naar het Plane work item

## Gevolgen

### Implementatie-impact

| Component | Wat te bouwen |
|-----------|---------------|
| MarQed | Analyse is bestaande functionaliteit |
| md-to-plane importer | Nieuw: parsed markdown, creëert Plane entities via API |
| Plane Sync Service | Sprint 2: inbound sync (Plane -> MQ DevEngine) |
| Change doc generator | Sprint 3: na feature completion, git diff + AI summary |

### Workflow-impact

- Ontwikkelaar moet 3 tools kennen: MarQed (analyse), Plane (planning), MQ DevEngine (monitoring)
- Git is de centrale bron van waarheid voor analyse-output
- Plane is de centrale bron van waarheid voor planning
- MQ DevEngine Feature DB is de executie-bron
