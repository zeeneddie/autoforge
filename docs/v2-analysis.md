# DevEngine v2 — Analyse

## De kernvraag

Hoe stuur ik een team van autonome LLM-agents aan zodat ik als product owner:
- kan vertrouwen op het resultaat
- kan zien wat er gebouwd wordt
- kan verifieren dat het goed gebouwd is
- de kosten kan verantwoorden

Dit is geen technisch vraagstuk. Dit is een management-vraagstuk.

---

## De MarQed Pipeline

DevEngine staat niet op zichzelf. Het is onderdeel van een keten:

```
mq-PO-Companion       mq-Planning        mq-DevEngine         mq-testing
────────────────       ───────────        ────────────         ──────────
Wat bouwen?            Waar staat het?    Hoe bouwen?          Werkt het?

PO definieert          mq-planning        Agents bouwen        PVA generatie
Epics/Features         Sprints/Cycles     code, tests,         Module tests
Stories + AC's         Status tracking    commits              Integratie tests
Kwaliteitscheck        Dependencies                            E2E tests
PO validatie                                                   UI verificatie
                                                               Triage
     │                      │                   │                   │
     └──────────────────────┘                   └───────────────────┘
          stories + AC's                        test specs + resultaten
          via mq-planning export                via API / webhooks
```

Elke schakel heeft een duidelijke verantwoordelijkheid:
- **PO-Companion**: INPUT-kwaliteit (WAT bouwen, hoe goed gedefinieerd)
- **Planning**: TRACKING (waar staan we, wat is gepland/bezig/klaar)
- **DevEngine**: EXECUTIE (code schrijven, deterministische checks, audit trail)
- **Testing**: VERIFICATIE (werkt het echt, op alle niveaus)

---

# DEEL I — INPUT: Wat ontvangt DevEngine?

## 1. Verantwoordelijkheid: mq-PO-Companion

De input-kwaliteit is NIET DevEngine's verantwoordelijkheid. Die is al geborgd upstream.

### 1.1 Wat PO-Companion levert

PO-Companion begeleidt de PO door 5 fasen:

```
Fase 1: Briefing    → brief.md (probleem, oplossing, doelgroep, constraints)
Fase 2: Capture     → req-raw.md (>=5 genummerde requirements + bronnen)
Fase 3: Structurize → prd.md (MoSCoW prioritering, NFR's, out-of-scope)
Fase 4: Visualize   → arch.md (tech stack, API contract, data model, diagrammen)
Fase 5: Decompose   → stories/*.md (user stories met AC's)
```

Elke fase-overgang wordt geblokkeerd door een gate validator totdat de kwaliteit voldoende is.

### 1.2 Kwaliteitsborging op input (PO-Companion's taak)

De sparring en kwaliteitschecks gebeuren in PO-Companion, niet in DevEngine:

```
PO schrijft feature:
  "Login flow"
  AC: "gebruiker kan inloggen"
       │
       ▼
SM agent (PO-Companion) analyseert:
       │
       ├── SPECIFIEKHEID
       │   ⚠ "gebruiker kan inloggen" is te vaag
       │     Voorstel: "POST /login retourneert 200 + JWT"
       │
       ├── TESTBAARHEID
       │   ⚠ Geen foutscenario's
       │     Voorstel: "POST /login met ongeldige credentials retourneert 401"
       │
       ├── VOLLEDIGHEID
       │   ⚠ Geen token expiry AC, geen logout AC, geen rate limiting
       │
       ├── HAALBAARHEID
       │   ⚠ Met alle AC's erbij: overweeg split in 2 features
       │
       └── PO VALIDEERT: goedkeuren, aanpassen, afwijzen, toevoegen
```

**Phase gates die kwaliteit afdwingen (PO-Companion):**

| Gate | Check | Drempel |
|---|---|---|
| G5.3 | Minimum AC's per story | >= 3 |
| G5.5 | Maximum story points | <= 8 |
| G5.6 | AC format (testbaar, specifiek) | regex: `^- \[ \] .{10,}` per AC |
| G5.7 | Must-Have coverage | Elke Must-Have requirement gedekt door >= 1 story |

### 1.3 Het contract: PO-Companion → mq-planning → DevEngine

PO-Companion exporteert naar mq-planning. DevEngine importeert van mq-planning.

**Wat DevEngine ontvangt per story:**

```
Story:
  name: "Auth endpoint met JWT"
  description: "POST /login accepteert email+wachtwoord, retourneert JWT"
  acceptance_criteria:
    - "POST /login met geldige credentials retourneert 200 + JWT token"
    - "POST /login met ongeldige credentials retourneert 401"
    - "JWT token bevat user_id en verloopt na 24 uur"
  priority: must (urgent in mq-planning)
  parent: "Feature: Login flow"
  cycle: "Sprint 3"
```

**Wat DevEngine NIET ontvangt maar wel nodig heeft:**

| Data | Beschikbaar in PO-Companion | Komt het door via mq-planning? | Gap? |
|---|---|---|---|
| Stories + AC's | Ja (fase 5) | Ja (export) | Nee |
| Tech stack | Ja (arch.md, fase 4) | Nee (niet in mq-planning issues) | JA |
| Database schema | Ja (arch.md) | Nee | JA |
| API contract | Ja (arch.md) | Nee | JA |
| UI design system | Deels (Excalidraw mockups) | Nee | JA |
| Feature grouping (Epics) | Ja (PRD structuur) | Deels (mq-planning parent issues) | DEELS |
| Story dependencies | Nee (niet in PO-Companion) | Nee | JA — DevEngine moet dit zelf bepalen |

**Conclusie**: De story-kwaliteit is geborgd. De architecturale context (tech stack, schema, API) moet nog een weg vinden van PO-Companion naar DevEngine — hetzij via een app_spec.txt generator, hetzij via een direct API endpoint.

### 1.4 DevEngine's eigen input-verwerking

DevEngine ontvangt gevalideerde stories maar moet zelf nog:

1. **Technische decompositie** (story planner):
   - Feature 1.1 "Login flow" → 3-8 implementation tasks
   - Bepaalt: welke files geraakt, welke volgorde, welke dependencies
   - Dit is TECHNISCH, niet functioneel — de functionele decompositie deed PO-Companion al

2. **Sizing voor LLM agents**:
   - Context radius: hoeveel files moet de agent begrijpen?
   - Wijziging scope: hoeveel files worden gewijzigd?
   - Complexiteit: standaard patroon of niche? (hallucinatie-risico)
   - File contention: raken meerdere agents dezelfde files?

3. **Dependency inference**:
   - Stories die dezelfde files raken → sequentieel plannen
   - Stories die op elkaars output bouwen → afhankelijkheid registreren

---

# DEEL II — EXECUTIE: Hoe werkt DevEngine?

## 2. Het beslismodel

### 2.1 Wie beslist wat?

```
BESLISSING                          WIE                  WANNEER
───────────────────────────────────────────────────────────────────
Welke features in sprint?           PO (via mq-planning)  Sprint planning
Zijn stories goed genoeg?           PO (in PO-Companion) Voor sprint start
Technische decompositie?            Story planner (LLM)  Bij sprint start
Welk model per story?               Orchestrator         Bij scheduling
Hoeveel parallelle agents?          Orchestrator         Runtime
Story opnieuw proberen?             Orchestrator         Na falen (max N retries)
Escaleren naar mens?                Orchestrator         Na max retries
Feature goedkeuren?                 Testing + Review     Na alle stories done
Sprint accepteren?                  PO                   Sprint review
```

### 2.2 Model selectie

```
Story complexiteit → Model keuze

Simpel (context radius 1-3 files, standaard CRUD):
  → haiku (goedkoop, snel, goed genoeg)

Medium (context radius 4-6 files, business logica):
  → sonnet (standaard keuze)

Complex (context radius 7+ files, architecturale beslissingen):
  → opus (duur, maar voorkomt hallucinatie en retries)

Retry na falen:
  → upgrade: haiku story faalt → retry met sonnet
  → upgrade: sonnet story faalt 2x → retry met opus
  → escalate: opus story faalt → mens
```

### 2.3 Retry strategie

```
Poging 1: origineel model
  │ faalt (deterministic check of test)
  ▼
Poging 2: zelfde model, foutmelding als extra context
  │ faalt
  ▼
Poging 3: upgrade model (haiku→sonnet, sonnet→opus)
  │ faalt
  ▼
ESCALATIE: story "blocked", PO krijgt notificatie
  PO kan:
  - AC's verduidelijken en opnieuw proberen
  - Story splitsen in kleinere stories
  - Story handmatig implementeren
  - Story uit sprint halen
```

### 2.4 Scheduling

```
Prioriteit factoren:
1. Dependencies: story 1.1.2 pas na 1.1.1
2. File contention: stories die dezelfde files raken → sequentieel
3. Kritisch pad: stories waar de meeste anderen op wachten → eerst
4. Kosten: goedkope stories (haiku) eerst voor efficient parallelisme
5. Risico: complexe stories eerder, zodat escalatie eerder zichtbaar is
```

---

## 3. Het validatiemodel

### 3.1 Vijf lagen van verificatie

```
Laag 1: AGENT SELF-CHECK (tijdens implementatie)
  Agent draait eigen tests, checkt eigen werk.
  Vertrouwensniveau: LAAG (agent is bevooroordeeld)

Laag 2: DETERMINISTISCHE POST-CHECKS (na story completion, door orchestrator)
  [ ] Lint + type-check
  [ ] Mock/fake data detectie
  [ ] Regressie suite (alle bestaande tests)
  [ ] Git commit met story ID aanwezig
  Vertrouwensniveau: HOOG voor syntactische correctheid

Laag 3: ONAFHANKELIJKE AGENT REVIEW (na feature completion)
  Testing agent: draait AC's opnieuw, test integratie
  Review agent: code kwaliteit, security, patterns
  Vertrouwensniveau: MEDIUM-HOOG

Laag 4: MQ-TESTING — GEAUTOMATISEERDE VERIFICATIE (na feature/sprint)
  Module tests: individuele componenten
  Integratie tests: samenwerking tussen componenten
  E2E tests: volledige user flows via Playwright
  UI verificatie: visuele controle, screenshots, layout checks
  Vertrouwensniveau: HOOG

Laag 5: MENSELIJKE REVIEW (sprint review of escalatie)
  PO: functionele acceptatie
  Tech lead: architectuur review
  Vertrouwensniveau: HOOGST
```

### 3.2 Wanneer welke laag?

```
Per USER STORY:   Laag 1 + Laag 2                 (altijd, automatisch)
Per USER STORY:   Laag 4 (module tests)            (DevEngine triggert mq-testing)
Per FEATURE:      Laag 3                           (altijd als review_enabled)
Per FEATURE:      Laag 4 (integratie + UI verif.)  (DevEngine triggert mq-testing)
Per SPRINT:       Laag 4 (full e2e suite)          (DevEngine triggert mq-testing)
Per SPRINT:       Laag 5                           (altijd, PO sprint review)
Bij ESCALATIE:    Laag 5                           (direct)
```

### 3.3 De volledige verificatie-keten per feature

```
Story 1 done ──→ deterministic checks ──→ mq-testing module tests
Story 2 done ──→ deterministic checks ──→ mq-testing module tests
Story 3 done ──→ deterministic checks ──→ mq-testing module tests
    │
    ▼
Alle stories done
    │
    ▼
DevEngine triggert mq-testing: FEATURE ACCEPTANCE TEST
    │
    ├── Integratie tests: stories werken samen
    ├── E2E user flow: volledige journey
    ├── UI verificatie: screenshots + layout
    │
    ▼
  ┌─── PASSED ────────────────────────────────┐
  │ Feature status → "getest" in mq-planning  │
  │ Wacht op sprint review door PO            │
  └───────────────────────────────────────────┘
  
  ┌─── FAILED ────────────────────────────────────────┐
  │ Triage: app_bug / test_bug / env                   │
  │ app_bug → DevEngine retry story                    │
  │ test_bug → mq-testing regenereert                  │
  │ onduidelijk → escalatie naar PO                    │
  │ mq-planning: feature terug naar "in bouw"          │
  └────────────────────────────────────────────────────┘
```

### 3.4 Wie checkt wat?

```
                CODING    ORCHESTRATOR  CODEX       MQ-TESTING          MENS
                AGENT     (determin.)   (reviewer)  (verificatie)       (PO)
                (Claude)  (post-checks) (OpenAI)    (module/integ/e2e)  (beslist)

PER STORY:
AC's geimpl.?    [x]                     [x]
Tests geschr.?   [x]       [x] count>0
Tests passing?              [x]
Lint passing?               [x]
Geen mock data?             [x]          [x]
Geen regressie?             [x]
Code kwaliteit?                          [x]
Security?                                [x]
Module tests?                                       [x] per AC

PER FEATURE:
Integratie?                                         [x] stories samen
E2E user flow?                                      [x] volledige journey
UI verificatie?                                     [x] screenshots + layout

PER SPRINT:
Full e2e suite?                                     [x] alle features
Triage bij falen?                                   [x] classificatie
Sprint acceptatie?                                                      [x]
```

**Codex vervangt de review agent.** Claude bouwt, Codex reviewt. Twee verschillende modellen = onafhankelijke beoordeling. Codex krijgt per story:
- De acceptance criteria
- De tech stack + architecturale constraints (uit arch.md)
- De feature/story beschrijving
- De DoD checklist
- De git diff van de wijzigingen

Codex beoordeelt: zijn de AC's geimplementeerd? Voldoet het aan de tech stack? Geen mock data? Code kwaliteit? Security? En rapporteert: APPROVE of REJECT met reden.

---

# DEEL III — OUTPUT: Wat levert DevEngine op?

DevEngine levert naar DRIE kanten:

```
                    ┌──────────────┐
                    │  DevEngine   │
                    │  (executie)  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        Het project    mq-testing    mq-Planning
        (code)         (verificatie) (tracking)
```

## 4. Output naar het project (code)

Per user story:
- **Code**: Nieuwe en gewijzigde bestanden
- **Tests**: Unit tests die AC's valideren
- **Git commit**: Met story ID in message (`feat(auth): add login [story-1.1.2]`)

Per feature:
- **Werkende functionaliteit**: Alle stories samen vormen de feature
- **Integratietests**: Tests die de samenhang valideren

Per sprint:
- **Deploybaar product**: Alle features samen, geen regressies

## 5. Output naar mq-testing (verificatie)

DevEngine moet mq-testing voeden zodat drie testniveaus uitgevoerd kunnen worden:

### 5.1 Module tests (per story)

```
DevEngine levert:                    mq-testing genereert:
─────────────────                    ────────────────────
Story ID + AC's                      Test specs per AC
Gewijzigde files                     Component-level tests
Tech stack info                      Assertions per AC
                                     → pytest of jest
```

### 5.2 Integratie tests (per feature)

```
DevEngine levert:                    mq-testing genereert:
─────────────────                    ────────────────────
Feature ID                           Cross-component tests
Alle stories in feature              API contract tests
Dependency graph                     Data flow tests
API endpoints aangemaakt             → pytest + httpx
```

### 5.3 E2E tests (per sprint)

```
DevEngine levert:                    mq-testing genereert:
─────────────────                    ────────────────────
Sprint scope (alle features)         Full user journey tests
Base URL (dev server)                Browser automation
User flows (van AC's)                → Playwright TypeScript
```

### 5.4 UI verificatie (per feature/sprint)

```
DevEngine levert:                    mq-testing genereert:
─────────────────                    ────────────────────
Base URL (dev server)                Screenshots per pagina
Verwachte pagina's/routes            Layout verificatie
Design system constraints            Visuele regressie checks
                                     Responsive checks
                                     → Playwright screenshots + vergelijking
```

### 5.5 Het contract: DevEngine → mq-testing

DevEngine moet per story/feature de volgende data beschikbaar maken:

```
TestRequest:
  story_id: "1.1.2"
  story_name: "Auth endpoint"
  acceptance_criteria:
    - id: "ac-001"
      text: "POST /login retourneert 200 + JWT"
      type: "functional"
    - id: "ac-002"
      text: "401 bij ongeldige credentials"
      type: "functional"
  files_changed:
    - path: "src/routes/auth.py"
      change_type: "modified"
    - path: "tests/test_auth.py"
      change_type: "created"
  tech_stack: "fastapi + sqlalchemy + postgresql"
  base_url: "http://localhost:3000"
  api_endpoints:
    - method: "POST"
      path: "/login"
      request_body: {email: string, password: string}
      response: {token: string}
```

### 5.6 Wie triggert mq-testing wanneer?

```
EVENT                        TRIGGER        MQ-TESTING ACTIE
──────────────────────────────────────────────────────────────────
Story done                   DevEngine  →   Module tests voor deze story
  (alle AC's passing,                       • Test per AC
  deterministic checks ok)                  • Component-level verificatie

Feature done                 DevEngine  →   Feature acceptance test
  (alle stories in feature                  • Integratie tests (stories samen)
  zijn done)                                • E2E user flow
                                            • UI verificatie (screenshots)
                                            • Cross-component tests
                                            
Sprint done                  DevEngine  →   Sprint-brede verificatie
  (alle features in sprint                  • Full e2e suite
  zijn done)                                • Regressie over hele applicatie
                                            • Performance baseline
                                            • Sprint test rapport
```

DevEngine is de trigger — die weet als eerste wanneer stories/features/sprint klaar zijn.
mq-planning is de SSOT voor status, niet de orchestrator.

Bij feature acceptance test failure:
```
mq-testing detecteert: integratie test "login flow" faalt
  │
  ├──→ mq-planning: comment op feature issue met failure details
  │    Feature status terug naar "in progress"
  │
  ├──→ DevEngine: failure report met:
  │    • welke stories betrokken
  │    • welke AC's falen in combinatie
  │    • triage: app_bug / test_bug / environment
  │
  └──→ Bij app_bug: DevEngine coding agent retry
       Bij test_bug: mq-testing regenereert test
       Bij onduidelijk: escalatie naar PO
```

### 5.7 Test resultaten terug naar DevEngine

mq-testing stuurt resultaten terug:

```
TestResults:
  story_id: "1.1.2"
  level: "module" | "integration" | "e2e" | "ui"
  results:
    - ac_id: "ac-001"
      test_ref: "HF-001"
      status: "passed"
      duration_ms: 1200
    - ac_id: "ac-002"
      test_ref: "EC-001"
      status: "failed"
      failure_class: "app_bug"    # app_bug | test_bug | flaky | environment | ac_unclear
      error: "Expected 401, got 500"
      screenshot: "screenshots/ec-001-fail.png"
      triage: "Missing error handler in auth_routes.py line 67"
  ui_verification:
    - page: "/login"
      screenshot: "screenshots/login-page.png"
      layout_check: "passed"
      responsive_check: "passed"
  summary:
    total: 8
    passed: 7
    failed: 1
    coverage: "87.5%"
```

**Bij falen**: DevEngine ontvangt het `failure_class`:
- `app_bug` → coding agent retry met foutmelding
- `test_bug` → mq-testing regenereert de test
- `flaky` → opnieuw draaien
- `environment` → dev server check
- `ac_unclear` → escalatie naar PO

## 6. Output naar mq-planning (tracking)

Status updates terug naar mq-planning:

```
Per story:  in_progress → completed (of blocked bij escalatie)
Per feature: aggregated status van alle stories
Per sprint:  velocity, burndown data
Commentaar:  falen-reden, escalatie details, test resultaten
```

---

# DEEL IV — Wat de PO ziet

## 7. Overzicht op vier niveaus

| Niveau | Vraag | Hoe de PO het ziet |
|---|---|---|
| Sprint | Waar staan we? Op schema? | Burndown, velocity, % done, kosten |
| Epic | Welke epics in scope? Hoe ver? | Epic progress bars |
| Feature | Klaar, bezig, gepland? | Kanban board (bestaand) |
| User Story | Wat doet de agent NU? | Goals view met stepper + accordeon |

### 7.1 Goals view — drie niveaus van zichtbaarheid

De oorspronkelijke vraag: "ik wil goals zien, niet tool-calls."

Oplossing: drie niveaus, progressief meer detail:

```
NIVEAU 1 — Altijd zichtbaar: AC's (WAT moet het doen)
NIVEAU 2 — Altijd zichtbaar: Taken (WELKE stappen neemt de agent)
NIVEAU 3 — Drill-down:       Tool calls (HOE — files, edits, commands)
```

### 7.2 Feature-niveau (in kanban/overzicht)

```
Feature: "Login flow"                                    IN BOUW   3/5

  Stories:
  ✓ DB session tabel         11 min   $0.45   3/3 AC's   module tests ✓
  ✓ Auth endpoint            14 min   $0.95   3/3 AC's   module tests ✓
  ⏳ JWT tokens               ← agent bezig
  ○ Login UI                  gepland
  ○ E2E tests                 gepland

  Feature acceptance test:    ○ wacht (alle stories moeten eerst done zijn)
```

### 7.3 Story-niveau (klik op story)

```
User Story: "Auth endpoint met JWT"                      GEVERIFIEERD

  Taken (DevEngine):                   Kosten: $0.95 | Duur: 14 min | Retries: 0
  ✓ 1. Database session tabel         Commit: a1b2c3d [story-1.1.2]
  ✓ 2. Auth endpoint route
  ✓ 3. JWT middleware
  ✓ 4. Error handling
  ✓ 5. Tests schrijven

  ──── Verificatie (van belangrijk naar minder belangrijk) ────

  ✅ AC's gevalideerd (mq-testing)             DOET HET WAT HET MOET DOEN?
     ✓ POST /login retourneert 200+JWT           (HF-001 PASSED)
     ✓ 401 bij foute credentials                 (EC-001 PASSED)
     ✓ JWT verloopt na 24u                       (HF-002 PASSED)

  ✅ E2E / UI geverifieerd (mq-testing)        WERKT HET VOOR DE GEBRUIKER?
     ✓ Login pagina laadt correct
     ✓ Formulier werkt
     ✓ Screenshot matcht verwachting

  ✅ Tests passing (agent)                     HEEFT DE BOUWER GETEST?
     ✓ 11/11 unit tests passing

  🟡 Lint + type-check (deterministic)         VOLDOET HET AAN STANDAARDEN?
     ✓ Lint: 0 errors, 0 warnings
     ✓ Type-check: 0 errors

  🟡 Mock check (deterministic)                GEEN NEPPE DATA?
     ✓ Geen mock/fake data gevonden

  🟡 Regressie (deterministic)                 BREEKT HET NIETS ANDERS?
     ✓ 42/42 bestaande tests passing

  ⬜ Code review (Codex)                        ONAFHANKELIJKE REVIEW
     ✓ AC's geimplementeerd: ja (3/3)
     ✓ Tech stack correct: FastAPI + PostgreSQL
     ✓ Geen mock data
     ✓ Geen security issues
     ✓ Clean patterns
     → APPROVED

  ⬜ PO geaccepteerd                           MENS HEEFT GEKEKEN
     ○ Wacht op sprint review
```

**De volgorde vertelt het verhaal** — van belangrijk naar minder belangrijk:

```
Rang  Vinkje                     Wat het bewijst              Bron
────  ─────────────────────────  ──────────────────────────── ──────────
1.    AC's gevalideerd           Functionaliteit werkt        mq-testing
2.    E2E / UI geverifieerd      Gebruiker kan ermee werken   mq-testing
3.    Codex review APPROVED      Onafhankelijk beoordeeld     Codex (OpenAI)
4.    Agent tests passing        Bouwer heeft zelf getest     DevEngine agent
5.    Lint + type-check          Voldoet aan standaarden      Orchestrator (det.)
6.    Mock check                 Geen neppe data              Orchestrator (det.)
7.    Regressie                  Breekt niets anders          Orchestrator (det.)
8.    PO geaccepteerd            Mens heeft goedgekeurd       PO (handmatig)
```

Elk vinkje voegt iets toe. De PO kan vertrouwen op de vinkjes omdat ze gerangschikt zijn: als #1 (AC's) groen is, werkt de functionaliteit. De rest voegt zekerheid toe maar het belangrijkste staat bovenaan.

### 7.4 Taak-niveau (drill-down op een taak)

```
  ▼ Taak 3: "JWT middleware"                             DONE

    Tests:
    ├── ✓ test_jwt_generates_valid_token         PASSED
    ├── ✓ test_jwt_contains_user_id              PASSED
    ├── ✓ test_jwt_expires_after_24h             PASSED
    └── ✓ test_jwt_rejects_tampered_token        PASSED

    Stappen:                                     (collapsed by default)
    ├── Read: src/routes/auth.py
    ├── Read: src/models/user.py
    ├── Edit: src/middleware/jwt.py (nieuw, 45 regels)
    ├── Edit: src/config/auth.py (regel 12-18 gewijzigd)
    └── Bash: pytest tests/test_jwt.py — 4/4 passed

    Duur: 4 min | Tokens: 12.400
```

### 7.5 Samenvatting: wat je ziet per niveau

```
NIVEAU          STANDAARD ZICHTBAAR           DRILL-DOWN
────────────────────────────────────────────────────────────────
Feature         Stories + status + kosten     Feature acceptance test resultaten
Story           AC's + Taken + verificatie    Taak details
Taak            Naam + status + tests         Tool calls (file edits, commands)
```

Per taak zijn de **tests** altijd zichtbaar (bewijs dat de taak goed is uitgevoerd).
De tool-calls (hoe de agent het deed) zijn collapsed by default — alleen voor debugging.

De drie bewijsniveaus per story:

```
Story "Auth endpoint"
│
├── Per TAAK: unit tests geschreven door de agent
│   Taak 1: 2 tests passing (tabel bestaat, kolommen kloppen)
│   Taak 2: 3 tests passing (endpoint, response format, error)
│   Taak 3: 4 tests passing (token generatie, expiry, validatie)
│   Taak 4: 2 tests passing (error handlers, logging)
│   Taak 5: -- (dit IS de test-taak)
│
├── Per STORY: deterministic checks door orchestrator
│   ✓ Lint   ✓ Type check   ✓ Mock check   ✓ Regressie (alle 11 tests)
│
└── Per STORY: module tests door mq-testing
    ✓ HF-001: login met geldige credentials → 200 + JWT
    ✓ EC-001: login met ongeldige credentials → 401
    ✓ HF-002: JWT bevat user_id, verloopt na 24u
```

**Dit geeft drie onafhankelijke bevestigingen dat de story correct is:**
1. Agent's eigen tests (per taak)
2. Orchestrator's deterministic checks (per story)
3. mq-testing's module tests (per AC)

### 7.2 Kosten-transparantie

```
Sprint 3: "User Management"

Budget: $25.00    Besteed: $18.40    Resterend: $6.60
████████████████████░░░░░  74%

Stories: 18 gepland  14 done  2 bezig  2 todo
First-pass success: 78%
Gem. kosten/story: $0.93
Duurste: 1.2.3 "Email templates" ($3.20) — 3 retries

Model verdeling:
Haiku:  40% stories  12% kosten
Sonnet: 55% stories  72% kosten
Opus:   5% stories   16% kosten

Test resultaten (mq-testing):
Module tests:      42/42 passed
Integratie tests:  12/14 passed (2 pending)
E2E tests:         8/8 passed
UI verificatie:    6/6 passed
```

---

# DEEL V — Traceerbaarheid

## 8. De audit trail

Per user story legt DevEngine vast:

```
Story 1.1.2: "Auth endpoint"
│
├── INPUT (van PO-Companion via mq-planning)
│   ├── Beschrijving + AC's (gevalideerd door PO)
│   ├── Context: architecture memory
│   └── Configuratie: model=sonnet, timeout=900s
│
├── EXECUTIE (DevEngine)
│   ├── Agent: "Spark", 14 min, 48K tokens, $0.18
│   ├── Retries: 0
│   ├── Files gewijzigd: auth_routes.py, test_auth.py
│   └── Git commit: a1b2c3d [story-1.1.2]
│
├── VERIFICATIE INTERN (DevEngine deterministic checks)
│   ├── [x] Lint: PASSED
│   ├── [x] Type check: PASSED
│   ├── [x] Mock check: PASSED (geen matches)
│   └── [x] Regressie: PASSED (42/42)
│
├── VERIFICATIE EXTERN (mq-testing)
│   ├── [x] Module tests: 3/3 PASSED (HF-001, EC-001, HF-002)
│   ├── [x] UI verificatie: /login screenshot ✓
│   └── [ ] E2E: wacht op feature completion
│
└── STATUS
    ├── Story: DONE
    ├── Feature: IN PROGRESS (3/5 stories done)
    └── mq-planning: synced (state: "completed")
```

## 9. Wat DevEngine nu vastlegt vs wat nodig is

| Data | Nu? | Nodig voor v2? |
|---|---|---|
| Feature beschrijving + AC's | Ja | Ja, behouden |
| Agent logs (tool calls) | Ja | Ja, koppelen aan story |
| Test results intern | Deels | Uitbreiden: per AC, per check type |
| Test results extern (mq-testing) | Nee | Ja: module, integratie, e2e, UI |
| Git commits per story | Nee | Ja: commit per story, story ID in message |
| Token usage | Nee | Ja: per story/feature/sprint |
| Kosten | Nee | Ja: model x tokens = kosten |
| Files gewijzigd per story | Nee | Ja: git diff per story |
| Screenshots / UI verificatie | Nee | Ja: via mq-testing |
| Duur per story | Deels | Ja: expliciet in DB |

---

# DEEL VI — Definition of Done

## 10. DoD per story

Een story mag pas als "done" gemarkeerd worden wanneer ALLE checks groen zijn.

### 10.1 Generieke DoD (geldt voor elk project)

```
USER STORY is DONE wanneer:

BOUW (coding agent)
[ ] Alle AC's zijn geimplementeerd (agent's eigen beoordeling)
[ ] Tests geschreven die AC's valideren
[ ] Code compileert zonder fouten

POST-CHECKS (orchestrator, deterministic)
[ ] Lint: 0 errors (exit code 0)
[ ] Type-check: 0 errors (exit code 0)
[ ] Mock data check: geen matches (exit code 1 van grep)
[ ] Regressie: alle bestaande tests passing
[ ] Test coverage: >= 80% van gewijzigde regels
[ ] Git commit aanwezig met story ID in message

REVIEW (Codex, onafhankelijk)
[ ] AC's geimplementeerd: bevestigd door Codex
[ ] Tech stack correct: conform arch.md
[ ] Geen security issues
[ ] Code kwaliteit voldoende
[ ] → APPROVED (of REJECT → retry, max 3x, daarna human in the loop)

VERIFICATIE (mq-testing, extern)
[ ] Module tests per AC: PASSED
[ ] UI verificatie (indien van toepassing): PASSED
```

### 10.2 Project-specifieke DoD uitbreidingen

Per project kan de DoD worden uitgebreid in `checks.yaml`:

```yaml
# .mq-devengine/checks.yaml
version: 1

# Generieke checks (altijd aan, niet uit te zetten)
# lint, type-check, mock-check, regressie, coverage, git-commit

# Project-specifieke checks
checks:
  server_restart_test:
    enabled: true
    run: "workflow/scripts/server_restart_test.sh"
    description: "Data persists na server restart"

  api_contract:
    enabled: true
    run: "npm run test:contract"
    description: "API responses matchen schema"

  accessibility:
    enabled: true
    run: "npx pa11y-ci"
    description: "WCAG 2.1 AA compliance"

  security_scan:
    enabled: true
    run: "npm audit --audit-level=high"
    description: "Geen high/critical vulnerabilities"

# Coverage drempel (default 80%)
coverage:
  minimum: 80
  scope: changed_files  # alleen gewijzigde files, niet hele codebase

# Codex review configuratie
review:
  max_retries: 3
  on_reject: retry_with_feedback  # coding agent krijgt reject-reden mee
  on_max_retries: escalate_to_po  # human in the loop via PO-Companion
```

### 10.3 Feature DoD

```
FEATURE is DONE wanneer:
[ ] Alle stories in de feature zijn DONE (volledige story DoD)
[ ] Feature acceptance test PASSED (mq-testing integratie + e2e + UI)
```

Geen eigen AC's — feature is een container. Done = alle stories done + integratie test passed.

### 10.4 Sprint DoD

```
SPRINT is DONE wanneer:
[ ] Alle geplande features zijn DONE
[ ] Full e2e suite PASSED (mq-testing)
[ ] Geen open regressies
[ ] Sprint report beschikbaar (kosten, kwaliteit, velocity)
[ ] PO heeft sprint review gedaan en geaccepteerd
```

### 10.5 De Codex reject-retry flow

```
Coding agent levert story op
  │
  ▼
Orchestrator: deterministic post-checks
  │ FAIL → terug naar coding agent met foutmelding
  │ PASS ↓
  ▼
Codex review: AC's + tech stack + kwaliteit
  │
  ├── APPROVED → door naar mq-testing
  │
  └── REJECTED (reden: "AC #2 niet geimplementeerd: endpoint retourneert 500 ipv 401")
      │
      ▼
      Poging 2: coding agent met reject-reden als context
      │ → Codex review
      │
      ├── APPROVED → door naar mq-testing
      └── REJECTED
          │
          ▼
          Poging 3: coding agent (model upgrade als beschikbaar)
          │ → Codex review
          │
          ├── APPROVED → door naar mq-testing
          └── REJECTED
              │
              ▼
              ESCALATIE → PO-Companion
              Story status: "blocked"
              PO krijgt: reject-reden, 3x retry history, kosten tot nu toe
              PO beslist: AC aanpassen / story splitsen / handmatig fixen
```

Elke retry telt mee in de kosten van de story. De PO kan in het kosten-dashboard zien welke stories duur waren door retries.

---

# DEEL VII — End-to-end flow

## 11. De complete flow: van PO-input tot done

```
FASE 0: DEFINITIE (mq-PO-Companion)
────────────────────────────────────
PO doorloopt 5 fasen:
  Briefing → Capture → Structurize → Architect → Decompose

Output:
  brief.md, prd.md, arch.md → gepusht naar mq-wiki
  stories + AC's → geexporteerd naar mq-planning

Gate: PO valideert stories. Pas na goedkeuring naar sprint.


FASE 1: SPRINT PLANNING (mq-planning)
─────────────────────────────────────────────────
PO wijst stories toe aan sprint (Cycle).
Stories staan onder Features (parent Issues) in Modules (Epics).

DevEngine importeert stories van mq-planning:
  → story naam, beschrijving, AC's
  → mq-planning IDs voor terugkoppeling

DevEngine leest project-context van mq-wiki:
  → arch.md (tech stack, schema, API contract)
  → prd.md (constraints, NFR's)


FASE 2: TECHNISCHE DECOMPOSITIE (DevEngine story planner)
──────────────────────────────────────────────────────────
Per story:
  Story planner analyseert:
    → AC's + architectuur context + bestaande codebase
  
  Output: 3-8 taken per story
    Taak 1: "Database migratie"
    Taak 2: "API endpoint"
    Taak 3: "Business logica"
    Taak 4: "Tests schrijven"

  Taken leven in DevEngine, niet in mq-planning.


FASE 3: IMPLEMENTATIE (DevEngine coding agent)
──────────────────────────────────────────────
Per story (mega-sessie, één agent):
  Agent ontvangt:
    → Story beschrijving + AC's
    → Taken van story planner
    → Architectuur context (uit mq-wiki)
    → Architecture memory (van voorgaande stories)

  Agent bouwt:
    → Code + tests per taak
    → Markeert taken als done via MCP tools

  UI toont: taken-voortgang + AC's als stepper


FASE 4: DETERMINISTIC POST-CHECKS (DevEngine orchestrator)
───────────────────────────────────────────────────────────
Orchestrator draait automatisch (agent kan niet overslaan):

  [ ] Lint + type-check           → exit code 0?
  [ ] Mock data check             → geen matches?
  [ ] Alle tests passing          → exit code 0?
  [ ] Test coverage >= 80%        → van gewijzigde files
  [ ] Project-specifieke checks   → uit checks.yaml

  FAIL → terug naar coding agent met foutmelding
  PASS → door naar Codex review


FASE 5: CODEX REVIEW (onafhankelijk)
─────────────────────────────────────
Codex (OpenAI) ontvangt:
  → Git diff van de story
  → AC's
  → Tech stack (arch.md)
  → DoD checklist

Codex beoordeelt:
  → AC's geimplementeerd? Ja/nee per AC
  → Tech stack correct?
  → Security issues?
  → Code kwaliteit?

  APPROVED → door naar fase 6
  REJECTED → terug naar fase 3 (max 3x, daarna PO escalatie)


FASE 6: GIT COMMIT (DevEngine orchestrator, deterministic)
───────────────────────────────────────────────────────────
Orchestrator maakt commit:
  "feat(auth): add login endpoint [story-1.1.2]"

Traceerbaarheid: story ID → git commit → gewijzigde files


FASE 7: MODULE TESTS (mq-testing, extern)
──────────────────────────────────────────
DevEngine triggert mq-testing:
  POST /api/v1/testing/runs/trigger
  Body: story + AC's + gewijzigde files + tech stack + base URL

mq-testing genereert en draait:
  → Test per AC (happy flow + edge cases)
  → UI verificatie (indien van toepassing)

  PASSED → story status "geverifieerd"
  FAILED → triage: app_bug / test_bug / environment
           app_bug → terug naar fase 3
           test_bug → mq-testing regenereert test
           onduidelijk → PO escalatie

Resultaten terug naar:
  → DevEngine (voortgang + audit trail)
  → mq-planning (comment op story issue)
  → PO-Companion (test overzicht)


FASE 8: FEATURE COMPLETION (automatisch)
─────────────────────────────────────────
Wanneer ALLE stories in een feature "geverifieerd" zijn:

DevEngine triggert mq-testing: FEATURE ACCEPTANCE TEST
  → Integratie tests (stories werken samen)
  → E2E user flow (volledige journey)
  → UI verificatie (screenshots per pagina)

  PASSED → feature status "getest" in mq-planning
  FAILED → PO-Companion notificatie, human in the loop


FASE 9: SPRINT REVIEW (PO, handmatig)
──────────────────────────────────────
Wanneer alle features in de sprint "getest" zijn:

PO reviewt in PO-Companion:
  → Sprint overzicht: features, stories, test resultaten
  → Kosten dashboard: budget, besteed, per story
  → Kwaliteitsmetrieken: first-pass success %, retries, escalaties
  → mq-testing rapport: module + integratie + e2e + UI resultaten

PO beslist:
  → ACCEPTED → sprint done, naar productie
  → FEEDBACK → specifieke stories/features terug naar DevEngine


FASE 10: STATUS SYNC (continu)
──────────────────────────────
Gedurende het hele proces:
  DevEngine → mq-planning: story status updates
  mq-testing → mq-planning: test resultaten als comments
  mq-testing → PO-Companion: compleet test overzicht
  Alle systemen → mq-wiki: kennis-accumulatie

Na sprint completion:
  mq-wiki genereert/update help pages per feature
  Help pages beschikbaar voor supportdesk
```

### 11.1 De flow visueel

```
PO-Companion        mq-planning     mq-wiki         DevEngine        mq-testing
────────────        ───────────     ───────         ─────────        ──────────
Definieert ──stories──→ Beheert                     
                        │                            
Pusht docs ─────────────────────→ Bewaart            
                        │           │                
                        stories ────────────→ Importeert
                                    │                │
                                    arch.md ─→ Leest context
                                                     │
                                              Story planner
                                                     │
                                              Coding agent
                                                     │
                                              Post-checks
                                                     │
                                              Codex review
                                                     │
                                              Git commit
                                                     │
                                              Triggert ──────────→ Module tests
                                                     │              │
                                    ←── resultaten ──────────────────┘
                        ←── status ──┘               │
                                              Feature done?
                                                     │
                                              Triggert ──────────→ Feature test
                                                     │              │
←── notificatie ──────────────────────────────────────────────────────┘
     PO review                                       
     │                                               
     ACCEPTED ──→ Done                               
```

---

# DEEL VIII — De rol van mq-wiki in de pipeline

## 12. Project-definitie: waar leeft het?

### 10.1 Het probleem

PO-Companion produceert rijke project-context (brief.md, prd.md, arch.md) die niet doorkomt via mq-planning. DevEngine heeft die context nodig. Maar er is ook een bredere vraag: wie bewaart de volledige project-kennis en maakt die doorzoekbaar?

### 10.2 Drie opties (alle drie nog open)

```
Optie A: mq-wiki als project-definitie hub (actieve rol)
  PO-Companion ──push──→ mq-wiki ←──API──── DevEngine
                                  ←──API──── mq-testing
                                  ←──API──── supportdesk
  + Unified API, knowledge graph, zoekbaar, linkbaar
  + Eén plek voor alle project-kennis
  - Extra dependency, mq-wiki moet uitgebreid worden

Optie B: Git als project-definitie hub (simpel)
  PO-Companion ──commit──→ project Git repo ←──leest── DevEngine
  + Simpel, geen extra systeem, versie-beheer gratis
  - Geen API, geen search, geen knowledge graph
  - Elk systeem moet zelf files parsen

Optie C: Hybride (Git als SSOT, mq-wiki als leeslaag)
  PO-Companion ──commit──→ Git (SSOT)
  mq-wiki ──indexeert──→ Git repos (read-only navigatie + search)
  DevEngine ──leest──→ Git (direct)
  Supportdesk ──leest──→ mq-wiki (via API of UI)
  + Git als bron van waarheid, mq-wiki als zoek/navigatie
  - Sync tussen Git en wiki moet onderhouden worden
```

### 10.3 De supportdesk-redenering: waarom mq-wiki meer is dan documentatie

De gebouwde applicatie heeft straks eindgebruikers. Die hebben vragen:

```
"Mijn login lukt niet"
"Ik kan geen mail sturen"
"Waar vind ik de rapportage?"
"Hoe voeg ik een nieuwe medewerker toe?"
"De pagina laadt niet na het opslaan"
```

De kennis om deze vragen te beantwoorden BESTAAT al — verspreid over de pipeline:

```
Vraag: "Mijn login lukt niet"

Relevante kennis:                           Waar leeft dit nu?
─────────────────                           ──────────────────
Hoe login werkt (functioneel)               PO-Companion: prd.md + stories
Hoe login gebouwd is (technisch)            DevEngine: code + arch.md
Welke fouten kunnen optreden                DevEngine: error handling in code
Welke tests het valideren                   mq-testing: test specs + resultaten
Bekende issues                              mq-planning: bug tickets
Schermafbeeldingen                          mq-testing: UI verificatie screenshots
```

Geen enkel systeem heeft het COMPLETE antwoord. De supportdesk heeft een kennislaag nodig die dit samenvoegt.

### 10.4 Kennislagen voor de supportdesk

```
Laag 1: WAT doet de applicatie?
  Bron: PO-Companion (prd.md, stories, AC's)
  Voorbeeld: "De login flow laat je inloggen met email en wachtwoord.
              Je ontvangt een JWT token dat 24 uur geldig is."

Laag 2: HOE werkt het (voor eindgebruikers)?
  Bron: Gegenereerd uit stories + AC's + UI screenshots
  Voorbeeld: "Ga naar /login. Vul je email en wachtwoord in.
              Klik op 'Inloggen'. Je wordt doorgestuurd naar het dashboard."
  Illustratie: screenshot van /login pagina (uit mq-testing UI verificatie)

Laag 3: WAT kan er fout gaan?
  Bron: AC's (error scenarios) + mq-testing edge case tests + bekende bugs
  Voorbeeld: "Als je wachtwoord onjuist is, zie je 'Ongeldige credentials'.
              Na 5 mislukte pogingen wordt je account tijdelijk geblokkeerd."

Laag 4: HOE los je het op?
  Bron: Gegenereerd uit error handling code + test triage + bug fixes
  Voorbeeld: "Controleer je caps lock. Gebruik 'Wachtwoord vergeten' als
              je wachtwoord niet werkt. Neem contact op met beheer als je
              account geblokkeerd is."
```

### 10.5 mq-wiki als kennishub: directe vs indirecte rol

**Directe rol: mq-wiki IS de supportdesk kennisbank**

```
mq-wiki (wiki-project-{naam})
├── entities/
│   ├── feature-login-flow.md        ← gegenereerd uit stories + AC's
│   ├── feature-registratie.md
│   └── feature-dashboard.md
├── concepts/
│   ├── jwt-token.md                 ← technisch concept, begrijpelijk gemaakt
│   ├── wachtwoord-beleid.md
│   └── rollen-en-rechten.md
├── help/
│   ├── login-problemen.md           ← FAQ gegenereerd uit error AC's + triage
│   ├── mail-versturen.md
│   └── rapportage-vinden.md
├── sources/
│   ├── prd.md                       ← origineel uit PO-Companion
│   ├── arch.md                      ← origineel uit PO-Companion
│   └── test-results-sprint-3.md     ← samenvatting uit mq-testing
└── graph/
    └── graph.json                   ← knowledge graph:
                                        feature → stories → help pages → known issues
```

De knowledge graph linkt alles:
```
[Feature: Login flow] ──→ [Story: Auth endpoint] ──→ [Help: Login problemen]
                                    │                         │
                                    ▼                         ▼
                          [Test: HF-001 PASSED]     [Known issue: #42 timeout]
                                    │
                                    ▼
                          [Screenshot: /login page]
```

**Indirecte rol: mq-wiki als bron, een overlay als interface**

```
Eindgebruiker ──vraagt──→  Support overlay (chatbot/FAQ)
                                │
                                ├── zoekt in mq-wiki via /api/search
                                ├── zoekt in mq-planning via API (open bugs)
                                └── genereert antwoord (RAG)
                                
De overlay combineert:
- mq-wiki kennis (hoe het werkt, wat kan fout gaan)
- mq-planning data (bekende bugs, geplande fixes)
- mq-testing screenshots (hoe het eruit hoort te zien)
```

### 10.6 De content-generatie keten

De help-content hoeft niet handmatig geschreven te worden. Het kan gegenereerd worden uit wat we al hebben:

```
PO-Companion                          mq-wiki help page
────────────                          ─────────────────
Story: "Auth endpoint"         →      # Login
AC: "POST /login retourneert          ## Hoe werkt het?
     200 + JWT bij geldige            Log in met je email en wachtwoord.
     credentials"                     Je sessie blijft 24 uur actief.
AC: "401 bij ongeldige         →      
     credentials"                     ## Problemen?
AC: "JWT verloopt na 24u"     →      - **Verkeerd wachtwoord**: Controleer
                                        caps lock. Gebruik "Wachtwoord
mq-testing                             vergeten" als het niet lukt.
─────────                             - **Account geblokkeerd**: Na 5
Screenshot: /login page        →        mislukte pogingen. Neem contact
Test: EC-001 "401 bij fout"   →        op met beheer.
                                      
mq-planning                           ## Bekend
───────────                           - #42: Timeout bij trage verbinding
Bug #42: "Login timeout"       →        (fix gepland in Sprint 4)
                                      
                                      ![Login pagina](/screenshots/login.png)
```

### 10.7 Wanneer wordt help-content gegenereerd?

```
EVENT                          ACTIE
──────────────────────────────────────────────────────────
Feature done + getest          → Genereer/update help pages voor deze feature
Bug aangemaakt in mq-planning  → Voeg "Bekend probleem" toe aan relevante help page
Bug opgelost                   → Verwijder "Bekend probleem", voeg toe aan changelog
Sprint done                    → Genereer sprint release notes
Nieuwe versie deployed         → Update alle screenshots (mq-testing UI verificatie)
```

### 10.8 De roadmap-connectie

mq-wiki's eigen ROADMAP noemt al "platform project-wiki als mq-brain module" met:
- Epic→Feature→Story→CustomerJourney→Help hierarchie
- Admin review queue voor LLM-gegenereerde help pages
- Coverage metrics (help-pages / stories × 100)
- Statisch geserveerde help pages (geen LLM, deterministic)
- Dynamische Q&A wanneer coverage ≥75% (RAG mode)

Dit past precies in het plaatje: mq-wiki evolueert van persoonlijke kennisbank naar platform-breed kennissysteem dat zowel de interne teams (PO, developers) als de eindgebruikers (supportdesk) bedient.

### 10.9 SSOT overzicht met mq-wiki

```
Systeem              SSOT voor                          Leest van
─────────────────────────────────────────────────────────────────────
mq-PO-Companion      Project-definitie (schrijft)       —
mq-Planning          Werkitems + status                 PO-Companion (stories)
mq-DevEngine         Implementatie + taken + kosten     mq-planning (stories), Git/wiki (context)
mq-testing           Verificatie + test resultaten      DevEngine (triggers), mq-planning (AC's)
mq-wiki              Project-kennis + help content      Alle bovenstaande (aggregeert)
Support overlay      Eindgebruiker-antwoorden           mq-wiki (kennis), mq-planning (bugs)
```

---

# DEEL VII — Open vragen

## 11. Beslissingen

### Q1. Hoe overbruggen we de gap PO-Companion → DevEngine?
Stories + AC's komen via mq-planning. Maar tech stack, schema, API contract staan in arch.md.
- A) app_spec.txt generator in PO-Companion
- B) DevEngine leest arch.md direct uit project Git
- C) Nieuwe API endpoint in PO-Companion die DevEngine kan aanroepen
- D) Via mq-wiki: PO-Companion pusht naar wiki, DevEngine leest van wiki API
- Zie DEEL VI sectie 10.2 voor uitgebreide analyse van de drie wiki-opties

### Q2. BESLOTEN: DevEngine triggert mq-testing
DevEngine triggert mq-testing op drie momenten:
- Story done → module tests
- Feature done (alle stories) → integratie + e2e + UI verificatie
- Sprint done → full suite + rapport
Via: POST /api/v1/testing/runs/trigger

### Q3. Hoe ontvangt DevEngine test resultaten van mq-testing?
- A) DevEngine pollt mq-testing API
- B) mq-testing webhook naar DevEngine bij test completion
- C) Beide systemen lezen/schrijven via mq-planning comments

### Q4. Git commit per story — hoe afdwingen?
- A) In de prompt: "commit na elke story met [story-ID]"
- B) Orchestrator doet de commit na story completion
- C) Hybrid: agent commit, orchestrator valideert story ID

### Q5. Hoe tracken we token-kosten?
- A) Claude Agent SDK exposeert usage stats
- B) Proxy/wrapper die API calls logt
- C) Schatting op basis van prompt/response lengte

### Q6. Past de Feature tabel voor een drielaagse hierarchie?
- Nu: Feature met parent_id. Geen formeel onderscheid Epic/Feature/Story.
- Optie: `level` kolom (epic=1, feature=2, story=3)
- Optie: Conventie via naamgeving (1 = epic, 1.1 = feature, 1.1.1 = story)

### Q7. Welke deterministische checks standaard aan?
- Lint + type-check: altijd?
- Mock data check: altijd?
- Full regression suite: altijd? (langzaam bij grote projecten)
- Server restart test: optioneel?

### Q8. Hoe verhoudt de testing agent (DevEngine intern) zich tot mq-testing?
- Optie A: Testing agent verdwijnt, mq-testing neemt alles over
- Optie B: Testing agent = snelle smoke test binnen DevEngine, mq-testing = uitgebreide verificatie
- Optie C: Testing agent blijft voor regressie, mq-testing voor functioneel + integratie + e2e
- Overweging: deterministic post-checks (lint, mock, regressie) vervangen al een deel van wat de testing agent deed

### Q9. UI verificatie — wanneer en hoe?
- Optie A: Na elke story met UI component: screenshot + visuele check
- Optie B: Na elke feature: volledige UI walkthrough
- Optie C: Alleen per sprint: e2e UI verificatie
- Vraag: Wie levert de design baseline? (PO-Companion Excalidraw mockups?)

### Q10. Wat is de MVP van v2?
- Optie minimaal: Goals view UI + deterministic post-checks + mq-testing webhook
- Optie midden: + kosten-tracking + traceerbaarheid + audit trail
- Optie volledig: + workflow engine + multi-sessie + model-per-stap

### Q11. Welke rol speelt mq-wiki?
- Optie A: Actieve hub — alle project-kennis leeft in mq-wiki, systemen lezen via API
- Optie B: Geen rol — Git is genoeg, mq-wiki blijft persoonlijke kennisbank
- Optie C: Hybride — Git als SSOT, mq-wiki als zoek/navigatie/kennislaag
- Zie DEEL VI voor volledige analyse inclusief supportdesk use case

### Q12. Help-content generatie: wanneer en door wie?
- Optie A: mq-wiki genereert automatisch help pages bij feature completion
- Optie B: Aparte agent/service die periodiek help-content genereert
- Optie C: Handmatig, buiten scope van v2
- Overweging: de content-bronnen bestaan al (AC's, screenshots, test results, bugs)

### Q13. Support overlay: apart systeem of in mq-wiki?
- Optie A: mq-wiki krijgt een chatbot/FAQ mode (RAG over help pages)
- Optie B: Apart support-systeem dat mq-wiki als kennisbron gebruikt
- Optie C: Buiten scope — eerst de kennislaag, dan de interface

---

# DEEL IX — Sprint Evolutie (visueel)

## Huidige situatie (v1)

```
  PO-Companion        mq-planning      DevEngine                    mq-testing
  +-----------+    +----------+    +----------------------+     +------------+
  | stories   |--->| Issues   |--->| "Feature" (alles)    |     | Niet       |
  | + AC's    |    | (flat)   |    |                      |     | gekoppeld  |
  |           |    |          |    | Agent bouwt          |     |            |
  | arch.md --+-X  |          |    | Agent zegt "klaar" X |     |            |
  | prd.md  --+-X  |          |    | Geen post-checks   X |     |            |
  |           |    |          |    | YOLO mode mogelijk  X |     |            |
  |           |    |          |    | Geen traceerbaarheid X|     |            |
  |           |    |          |    | Geen kosten inzicht X |     |            |
  +-----------+    +----------+    +----------------------+     +------------+

  mq-wiki                                PO ziet:
  +-----------+                          - Kanban
  | Persoon-  |                          - Tool calls
  | lijke     |                          - Geen goals
  | kennisbank|
  +-----------+
```

## Sprint 0: Post-checks (6 dagen) — 80% kwaliteitsverbetering

```
  DevEngine
  +----------------------------------------------+
  |                                              |
  | Agent bouwt                                  |
  |   |                                          |
  |   v                                          |
  | +------------------------------------------+ |
  | | POST-CHECKS (NEW)                        | |
  | | [x] Lint          [x] Mock grep          | |
  | | [x] Tests         [x] Coverage >= 80%    | |
  | |                                          | |
  | | FAIL -> retry agent met foutmelding      | |
  | | PASS -> mark done                        | |
  | +------------------------------------------+ |
  |                                              |
  | YOLO verwijderd. checks.yaml configureerbaar.|
  +----------------------------------------------+
  
  Alleen mq-devEngine verandert. Geen dependencies.
```

## Sprint 1: DevEngine kern (12 dagen) — traceerbaarheid + Codex review

```
  mq-planning        DevEngine                              Codex (OpenAI)
  +----------+    +----------------------------------+    +----------+
  | Module   |--->| Story tabel (RENAMED)            |    |          |
  | =Epic    |    | acceptance_criteria (RENAMED)     |    | Reviews: |
  | Cycle    |    |                                  |    | AC's?    |
  | =Sprint  |    | Agent bouwt                      |    | Tech?    |
  | Issue    |    |   |                              |    | Secure?  |
  | =Story   |    |   v                              |    | Clean?   |
  |          |    | Post-checks                      |    |          |
  |          |    |   |                              |    | APPROVE  |
  |          |    |   v                 max 3x       |    |  of      |
  |          |    | Codex review <------retry---------+----| REJECT   |
  |          |    |   |                              |    |  |       |
  |          |    |   v                              |    |  v       |
  |          |    | Git commit [story-1.1.2]         |    |  PO      |
  |          |    |                                  |    +----------+
  |          |    | UI: Goals view                   |
  |          |    | +------------------------------+ |
  |          |    | | V AC's (mq-testing)           | |
  |          |    | | V Codex APPROVED              | |
  |          |    | | V Agent tests                 | |
  |          |    | | o Lint + type-check            | |
  |          |    | | o Mock + regressie             | |
  |          |    | | _ PO geaccepteerd              | |
  |          |    | +------------------------------+ |
  +----------+    +----------------------------------+
```

## Sprint 2: Wiki + API contracts (6 dagen) — tech stack context

```
  PO-Companion       mq-wiki                DevEngine
  +-----------+    +------------------+    +----------------+
  |           |    | wiki-project-{x} |    |                |
  | arch.md --+--->| sources/         |--->| Leest:         |
  | prd.md  --+--->|   arch.md        |    |  tech stack    |
  |           |    |   prd.md         |    |  constraints   |
  |   PUSH    |    |   brief.md       |    |                |
  +-----------+    |                  |    | Agent krijgt   |
                   | API:             |    | context mee    |
                   | /api/entity/...  |    +----------------+
                   +------------------+

  mq-platform: API CONTRACTS VASTGELEGD
  DevEngine <-> mq-testing trigger + resultaten format
  mq-testing <-> PO-Companion resultaten format
```

## Sprint 3: mq-testing integratie (12 dagen) — verificatie-piramide compleet

```
  DevEngine                                  mq-testing
  +----------------------------+          +------------------+
  |                            |          |                  |
  | Story done  ---------------+--------->| Module tests     |
  |                            |<---------| per AC           |
  |                            |          |                  |
  | Feature done --------------+--------->| Integratie tests |
  | (alle stories)             |          | E2E user flow    |
  |                            |          | UI verificatie   |
  |                            |          | Load test        |
  |                            |<---------| PASS / FAIL      |
  |                            |          |                  |
  | Sprint done ---------------+--------->| Full suite       |
  |                            |          | Sprint rapport   |
  +----------------------------+          +------------------+
         |            |                          |
         v            v                          v
     mq-planning  PO-Companion              PO-Companion
     (status)    (test overzicht)         (test overzicht)
```

## Sprint 4: PO feedback loop (6 dagen) — PO ziet alles

```
  PO-Companion
  +--------------------------------------------+
  | PORTFOLIO VIEW                             |
  |                                            |
  | Epic: User Management               60%   |
  | +- Feature: Login flow         GETEST     |<--- mq-planning (status)
  | |  +- Story: DB tabel           V         |
  | |  +- Story: Auth endpoint      V         |<--- DevEngine (voortgang + kosten)
  | |  +- Story: JWT tokens         o         |
  | +- Feature: Registratie        GEPLAND    |<--- mq-testing (test resultaten)
  |                                            |
  | KOSTEN: Budget $25 | Besteed $18 | Rest $7|<--- DevEngine (kosten API)
  |                                            |
  | ESCALATIE:                                 |
  | ! Story 1.2.3 blocked (Codex reject 3x)   |<--- DevEngine (escalatie)
  |   [AC aanpassen] [Splitsen] [Handmatig]    |
  +--------------------------------------------+
```

## Sprint 5: Help-content + support (6 dagen) — kennisbron voor supportdesk

```
  mq-wiki
  +--------------------------------------------------+
  | wiki-project-{x}                                  |
  |                                                   |
  | sources/            <--- PO-Companion             |
  |   arch.md, prd.md                                 |
  |                                                   |
  | entities/           <--- auto-generated           |
  |   feature-login-flow.md    bij feature done       |
  |                                                   |
  | help/               <--- auto-generated           |
  |   inloggen.md              uit AC's + errors      |
  |   account-aanmaken.md      + screenshots          |
  |                                                   |
  | reports/            <--- auto-generated           |
  |   sprint-3-report.md      kosten + kwaliteit      |
  |                                                   |
  | graph/                                            |
  |   feature --> story --> help --> bug               |
  |                                                   |
  | /help  (FAQ zoek-interface)                       |
  |   "login lukt niet" --> help/inloggen.md          |
  +--------------------------------------------------+
                    |
                    v
           +----------------+
           | Supportdesk    |
           | zoekt in wiki  |
           | vindt antwoord |
           +----------------+
```

## Eindresultaat: de complete pipeline

```
  PO-Companion       mq-planning  mq-wiki        DevEngine       mq-testing
  +-------------+  +----------+  +-----------+  +-------------+  +----------+
  | Definieert  |  | Beheert  |  | Bewaart   |  | Bouwt       |  |Verifieert|
  |             |  |          |  |           |  |             |  |          |
  | stories ----|->| Issues --|->| context --|->| importeert  |  |          |
  | AC's        |  | Cycles   |  | arch.md   |  | story plan  |  |          |
  | arch.md ----|--+----------|->| prd.md    |  | agent bouwt |  |          |
  |             |  |          |  |           |  | post-checks |  |          |
  | PO valideert|  |          |  |           |  | Codex review|  |          |
  |             |  |          |  |           |  | git commit  |  |          |
  |             |  |          |  |           |  |      |      |  |          |
  |             |  |          |  |           |  | story done--+->| module   |
  |             |  |          |  |           |  |             |<-| tests    |
  |             |  |          |  |           |  | feat. done--+->| integ.   |
  |             |  |          |  |           |  |             |<-| e2e + UI |
  |             |  |          |  |           |  |             |  | load     |
  | <-----------+--+----------+--+-----------+--+-------------+--| rapport  |
  | portfolio   |  |<-status--|  |<-help-----|  |             |  |          |
  | kosten      |  | comments |  |  content  |  |             |  |          |
  | escalatie   |  |          |  |  graphs   |  |             |  |          |
  | test result.|  |          |  |           |  |             |  |          |
  +-------------+  +----------+  +-----------+  +-------------+  +----------+

  SSOT per domein:
    PO-Companion = definitie + validatie
    mq-planning  = werkitems + status
    mq-wiki      = project-kennis + help
    DevEngine    = implementatie + kosten
    mq-testing   = verificatie + resultaten
```
