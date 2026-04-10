# MarQed Platform — Terminologie & Framing

## Doel

Eenduidige taal over het hele platform. Dezelfde woorden in de UI, in de code, in de API's, in de documentatie. Eerst de UI (wat de PO ziet), daarna de code (hoe het geimplementeerd is).

---

## 1. De canonieke hierarchie

```
EPIC                                        CONTAINER — geen AC's
  Een groot thema dat meerdere sprints kan beslaan.
  Voorbeeld: "User Management"
  Eigenaar: PO
  Bevat: 3-10 Features
  Done: wanneer ALLE features done zijn
  Heeft: beschrijving, GEEN acceptance criteria

  FEATURE                                   CONTAINER — geen AC's
    Een afgesloten stuk functionaliteit dat waarde levert.
    Voorbeeld: "Login flow"
    Eigenaar: PO
    Bevat: 3-8 User Stories
    Done: wanneer ALLE stories done zijn
    Heeft: beschrijving, GEEN acceptance criteria
    Verificatie: mq-testing integratietest (afgeleid van stories' AC's)

    USER STORY                              WERKITEM — heeft AC's
      De kleinste eenheid werk die een agent bouwt.
      Voorbeeld: "Auth endpoint met JWT"
      Eigenaar: Story planner (technisch) + PO (validatie)
      Bevat: 3-5 Acceptance Criteria
      Done: alle AC's passing + deterministic checks + tests
      Heeft: beschrijving + acceptance criteria
      
      ACCEPTANCE CRITERION (AC)
        Een toetsbare uitspraak over het gewenste gedrag.
        Voorbeeld: "POST /login retourneert 200 + JWT bij geldige credentials"
        Eigenaar: PO (via PO-Companion)
        Toetsbaar door: agent tests + deterministic checks + mq-testing

      TAAK                                        INTERN DEVENGINE
        Een technische implementatiestap binnen een story.
        Voorbeeld: "Maak database migratie voor sessions tabel"
        Eigenaar: Story planner (DevEngine, automatisch)
        Zichtbaar: in DevEngine UI, NIET in mq-planning
        Drill-down: tool-calls per taak (file edits, bash commands)
```

### Kernprincipe: alleen stories hebben AC's, alleen stories hebben taken

```
Epic:    beschrijving    GEEN AC's    done = alle features done      mq-planning
Feature: beschrijving    GEEN AC's    done = alle stories done       mq-planning
Story:   beschrijving    WEL AC's     done = alle AC's + checks      mq-planning + DevEngine
  Taak:  beschrijving    geen AC's    done = agent heeft het gedaan  DevEngine intern
```

Features en epics zijn CONTAINERS. Ze aggregeren status omhoog.
Alleen stories zijn WERKITEMS die de agent bouwt en die AC's hebben.

Feature-level verificatie (bv. "werkt de login flow end-to-end?") is GEEN AC
op de feature — het is een integratietest die mq-testing genereert op basis
van de stories' AC's.

---

## 2. Mapping naar mq-planning

### mq-planning concepten → MarQed concepten

mq-planning is een fork van [Plane](https://github.com/makeplane/plane). We gebruiken de native Plane concepten:

```
mq-planning concept  MarQed              Waarom
────────────────────────────────────────────────────
Module               Epic                Langlopende container over sprints heen
Cycle                Sprint              Tijdgebonden iteratie
Issue (parent)       Feature             Container, groepeert stories
Issue (leaf)         User Story          Werkitem met AC's
Issue description    AC's                Testbare criteria in de description
```

Geen custom fields of labels nodig — we gebruiken Plane's eigen structuur.

### Voorbeeld in mq-planning

```
Module: "User Management"                              = Epic
  Cycle: "Sprint 3"                                    = Sprint
    Issue: "Login flow"                                = Feature (parent)
      Issue: "DB session tabel"      [AC's in descr]  = Story (leaf)
      Issue: "Auth endpoint"         [AC's in descr]  = Story (leaf)
      Issue: "JWT tokens"            [AC's in descr]  = Story (leaf)
    Issue: "Registratie"                               = Feature (parent)
      Issue: "Registratie formulier" [AC's in descr]  = Story (leaf)
      Issue: "Email verificatie"     [AC's in descr]  = Story (leaf)
```

---

## 3. Huidige terminologie per systeem

### mq-PO-Companion

| Concept | Huidige term | Waar | Opmerking |
|---|---|---|---|
| Epic | (impliciet in PRD) | prd.md | Niet expliciet |
| Feature | "Feature" | stories fase 5 | Soms verward met story |
| User Story | "Story" | stories/story-001.md | Goed gedefinieerd, heeft AC's |
| AC | "Acceptance Criteria" | In story markdown | Gate G5.6 valideert formaat |

### mq-planning

| Concept | mq-planning term | Opmerking |
|---|---|---|
| Epic | Module | Native Plane concept |
| Sprint | Cycle | Native Plane concept |
| Feature | Issue (parent) | Issue met child-issues |
| User Story | Issue (leaf) | Issue zonder kinderen, AC's in description |

### mq-DevEngine

| Concept | Huidige term | Probleem |
|---|---|---|
| Epic | Feature (diepte 0) | VERWARREND — alles heet "feature" |
| Feature | Feature (diepte 1) | VERWARREND |
| User Story | Feature (diepte 2) of "sub-feature" | VERWARREND |
| AC | "steps" (JSON array) | MISLEIDEND — steps ≠ acceptance criteria |
| Sprint | - | ONTBREEKT als concept |

**Kernprobleem**: DevEngine noemt alles een "Feature" en hoeft het verschil niet te weten. DevEngine bouwt alleen stories (leaf nodes). De hierarchie is mq-planning's verantwoordelijkheid.

### mq-testing

| Concept | Huidige term | Opmerking |
|---|---|---|
| Epic | Entity (type: epic) | Van mq-discover |
| Feature | Entity (type: story) | Verwarrend naming in discover |
| User Story | Entity (type: task) | Verwarrend naming in discover |
| AC | acceptance_criteria | Goed gedefinieerd |

---

## 4. De gewenste terminologie

### In de UI (wat de PO ziet)

```
Platform-breed gebruiken we ALTIJD:

  Epic           (nooit: "parent feature", "top-level feature", "module")
  Feature        (nooit: "container", "parent story", "epic item")
  User Story     (nooit: "sub-feature", "task", "item", "issue")
  Sprint         (nooit: "cycle", "iteration", "batch")
  AC             (nooit: "step", "test case", "criterion")
  
  Status termen:
  In definitie   — PO werkt eraan in PO-Companion
  Gevalideerd    — PO heeft goedgekeurd
  Gepland        — In sprint gezet
  In bouw        — Agent werkt eraan
  Geverifieerd   — Deterministic checks + tests passed
  Getest         — mq-testing module/integratie/e2e passed
  Geaccepteerd   — PO heeft sprint review gedaan
  In productie   — Deployed
  Geblokkeerd    — Escalatie, wacht op mens
```

### In de code (DevEngine)

DevEngine hoeft het verschil tussen epic en feature NIET te weten.
DevEngine bouwt user stories. De hierarchie is mq-planning's verantwoordelijkheid.

```
Database:
  Feature tabel BLIJFT — maar bevat alleen stories (leaf nodes)
  Container-features (epics/features) bestaan in mq-planning, niet in DevEngine
  
  Feature.steps → hernoem naar acceptance_criteria
  Feature.tasks → verdwijnt (sub-features zijn aparte Feature records)
  
  Toevoegen:
  Feature.planning_module_id  → link naar mq-planning Module (epic)
  Feature.planning_cycle_id   → link naar mq-planning Cycle (sprint)
  Feature.planning_parent_id  → link naar mq-planning parent issue (feature)

DevEngine weet per story:
  - story ID + beschrijving + AC's
  - bij welke mq-planning cycle (sprint) het hoort
  - bij welke mq-planning parent issue (feature) het hoort
  - bij welke mq-planning module (epic) het hoort
  
DevEngine hoeft NIET te weten:
  - hoeveel andere stories de feature heeft
  - wanneer de feature "done" is (dat berekent mq-planning)
  - wat de epic-beschrijving is
```

### In de API's

```
DevEngine API:
  GET /api/projects/{name}/stories              ← alle stories (was: /features)
  GET /api/projects/{name}/stories?sprint=3     ← stories in sprint
  GET /api/projects/{name}/stories/{id}         ← story detail + AC's
  
  Status: mq-planning berekent feature/epic completion
  DevEngine rapporteert alleen story-level status

mq-planning:
  Module = Epic    (native Plane concept)
  Cycle  = Sprint  (native Plane concept)
  Issue  = Feature (parent) of Story (leaf)
  
mq-testing API:
  Ontvangt stories + AC's van DevEngine of mq-planning
  Rapporteert test resultaten per story terug
```

---

## 4. Mapping: wat moet waar veranderen?

### mq-PO-Companion

| Wat | Nu | Wordt | Impact |
|---|---|---|---|
| Fase 5 output | "stories" | "User Stories" (expliciet) | Alleen labeling |
| PRD structuur | Vrije tekst | Expliciete Epics/Features | Template aanpassen |
| Export naar mq-planning | Issues (flat) | Issues met level label | Export logica aanpassen |

### mq-planning

| Wat | Nu | Wordt | Impact |
|---|---|---|---|
| Issue types | Allemaal "Issue" | Label: epic/feature/story | Labels of custom fields toevoegen |
| Nesting | Parent-child | Parent-child + level label | Minimaal |

### mq-DevEngine

| Wat | Nu | Wordt | Impact |
|---|---|---|---|
| DB: Feature tabel | Alles is "Feature" | Feature + level kolom | **Migratie nodig** |
| DB: Feature.steps | "steps" | "acceptance_criteria" | **Kolom rename + migratie** |
| DB: Feature.tasks | JSON blob | Verdwijnt (sub-features) | **Data migratie** |
| UI: Kanban header | "Features" | "Epics" / "Features" / "Stories" per niveau | **UI aanpassing** |
| UI: FeatureCard | Geen level indicatie | Badge: EPIC / FEATURE / STORY | **Component aanpassing** |
| UI: FeatureModal | "Test Steps" | "Acceptance Criteria" | **Label aanpassing** |
| API: endpoints | /features (alles) | /epics, /features, /stories of /work-items?level= | **API herstructurering** |
| MCP: tools | feature_get_summary | Behoud (intern), maar output labels aanpassen | **Minimaal** |
| Code: variabelen | feature, sub_feature | epic, feature, story | **Refactor** |
| Prompts | "feature" overal | "user story" waar het een story betreft | **Prompt templates** |
| WebSocket | feature_update | story_update / feature_update / epic_update | **Protocol uitbreiding** |

### mq-testing

| Wat | Nu | Wordt | Impact |
|---|---|---|---|
| Input: entities | "entity" (type: epic/story/task) | epic/feature/story | Mapping aanpassen |
| API docs | "entity" termen | epic/feature/story termen | Documentatie |

---

## 5. De UI framing — wat de PO ziet

### Kanban board (DevEngine UI)

Nu:
```
┌──────────────┬──────────────┬──────────────┐
│   PENDING    │  IN PROGRESS │    DONE      │
├──────────────┼──────────────┼──────────────┤
│ Feature 3    │ Feature 1    │ Feature 2    │
│ Feature 4    │              │              │
└──────────────┴──────────────┴──────────────┘
```

Wordt (met level-aware weergave):
```
Epic: User Management                              ████████░░ 60%
┌──────────────┬──────────────┬──────────────┐
│   BACKLOG    │    IN BOUW   │ GEVERIFIEERD │
├──────────────┼──────────────┼──────────────┤
│              │ ┌──────────┐ │ ┌──────────┐ │
│              │ │ FEATURE   │ │ │ FEATURE   │ │
│              │ │ Login flow│ │ │ Registr.  │ │
│              │ │ 3/5 stories│ │ │ 5/5 ✓     │ │
│              │ │ ⏳ JWT...  │ │ │ tested ✓  │ │
│              │ └──────────┘ │ └──────────┘ │
└──────────────┴──────────────┴──────────────┘

  Klik op Feature "Login flow":
  ┌─────────────────────────────────────┐
  │ Feature: Login flow                 │
  │ Epic: User Management              │
  │ Sprint: Sprint 3                   │
  │                                     │
  │ User Stories:                       │
  │ ✅ DB session tabel      $0.45      │
  │ ✅ Auth endpoint         $0.95      │
  │ 🔨 JWT tokens            (bezig)    │
  │ ⏳ Login UI              (wacht)    │
  │ ⏳ E2E tests             (wacht)    │
  │                                     │
  │ Acceptance Criteria:                │
  │ ✅ POST /login retourneert 200+JWT  │
  │ ✅ 401 bij foute credentials        │
  │ ⏳ JWT verloopt na 24u              │
  │ ⏳ 403 zonder geldig token          │
  └─────────────────────────────────────┘
```

### PO-Companion portfolio view

```
┌─────────────────────────────────────────────────┐
│ Mijn projecten — Portfolio                      │
│                                                 │
│ Project: FysioOne v2.0                          │
│                                                 │
│ Sprint 3: "User Management"    Budget: $25      │
│                                                 │
│ EPIC: User Management                     60%   │
│ ├── FEATURE: Login flow            IN BOUW      │
│ │   ├── STORY: DB session tabel    ✅ Geverif.  │
│ │   ├── STORY: Auth endpoint       ✅ Geverif.  │
│ │   ├── STORY: JWT tokens          🔨 In bouw   │
│ │   ├── STORY: Login UI            ⏳ Wacht     │
│ │   └── STORY: E2E tests           ⏳ Wacht     │
│ ├── FEATURE: Registratie           ✅ Getest    │
│ └── FEATURE: Wachtwoord reset      📋 Gepland   │
│                                                 │
│ EPIC: Dashboard                           0%    │
│ ├── FEATURE: Analytics widget      ✏️ In defin. │
│ └── FEATURE: Activity feed         ✏️ In defin. │
│                                                 │
│ Legende:                                        │
│ ✏️ In definitie (PO-Companion)                   │
│ 📋 Gepland (in sprint, wacht op agent)           │
│ 🔨 In bouw (agent werkt eraan)                   │
│ ✅ Geverifieerd/Getest                           │
│ 🚀 In productie                                 │
│ 🚫 Geblokkeerd                                   │
└─────────────────────────────────────────────────┘
```

---

## 6. Beslissingen

### BESLOTEN

| Beslissing | Keuze | Reden |
|---|---|---|
| mq-planning mapping | Module=Epic, Cycle=Sprint, Issue=Feature/Story | Gebruikt native Plane concepten |
| Alleen stories hebben AC's | Ja | Features/epics zijn containers, stories zijn werkitems |
| DevEngine kent geen epics/features | Ja | DevEngine bouwt stories, mq-planning beheert hierarchie |
| Feature.steps → acceptance_criteria | Ja | Correcte terminologie, migratiescript nodig |
| Feature.tasks → verdwijnt | Ja | Sub-features zijn aparte Feature records |

### NOG TE BESLISSEN

### B1. Feature tabel hernoemen naar Story?
- Optie A: Behoud "Feature" tabel naam (minder migratie, maar verwarrend)
- Optie B: Hernoem naar "Story" (consequent, maar breaking change)
- Optie C: Hernoem naar "WorkItem" (generiek, maar niemand zegt "work item")

### B2. Wanneer doorvoeren?
- Optie A: Bij v2 launch (clean break)
- Optie B: Geleidelijk (DB rename later, UI labels eerst)

### B3. Hoe rapporteert DevEngine story completion naar mq-planning?
- Nu: outbound_sync zet issue state op "completed"
- Nieuw nodig: ook deterministic check results en mq-testing results als comments?
