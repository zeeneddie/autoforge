# DevEngine v2 — Ideaalplaatje & Ontbrekende Puzzelstukken

## Jouw visie (samengevat)

```
Project
├── Epic 1: User Management
│   ├── Feature 1.1: Login flow
│   │   ├── User Story 1.1.1: Database session tabel
│   │   ├── User Story 1.1.2: Auth endpoint
│   │   └── User Story 1.1.3: JWT tokens
│   └── Feature 1.2: Registration
│       ├── User Story 1.2.1: Registratie formulier
│       └── User Story 1.2.2: Email verificatie
└── Epic 2: Dashboard
    └── ...
```

Scrum/agile werkwijze:
- Sprints met geplande features
- Story planner breekt features op in user stories
- Acceptance criteria per story, testbaar
- Stappen auditeerbaar en controleerbaar
- Kosten (tokens) afgewogen tegen kwaliteit en navolgbaarheid

## Wat je beschrijft en wat daarin werkt

| Jouw punt | Waarom het goed is |
|---|---|
| Epics/Features/Stories hierarchie | Geeft overzicht op drie niveaus — strategisch, tactisch, operationeel |
| Story planner voor sprint vulling | Automatische decomposie voorkomt te grote taken |
| AC's helder en testbaar | Objectieve maatstaf voor "klaar" |
| Stappen controleerbaar/auditeerbaar | Vertrouwen in het proces, niet alleen het resultaat |
| Kosten vs kwaliteit afweging | Pragmatisch — niet alles hoeft opus te zijn |

---

## Wat je mist

### 1. Sizing-model voor LLM agents (niet story points)

Story points meten **menselijke inspanning**. Voor LLM agents is de beperkende factor anders:

| Menselijke factor | LLM factor | Waarom het verschilt |
|---|---|---|
| Complexiteit van logica | **Context radius** — hoeveel files moet de agent begrijpen? | Een mens kan 20 files in z'n hoofd houden. Een LLM heeft een context window. |
| Ervaring van de developer | **Patroon-herkenbaarheid** — lijkt het op trainingsdata? | Standaard CRUD = makkelijk. Niche protocol = hallucinatie-risico. |
| Uren werk | **Token budget** — hoeveel tokens kost het? | Meer tokens ≠ betere output na een bepaald punt. |
| Team-afhankelijkheid | **File contention** — raken meerdere agents dezelfde files? | Merge conflicts bij parallelle agents. |

**Wat je nodig hebt**: Een sizing-model dat per user story inschat:

```
User Story 1.1.2: "Auth endpoint"
├── Context radius: 4 files (auth.py, routes.py, models.py, test_auth.py)
├── Wijziging scope: 2 files (routes.py, test_auth.py)
├── Complexiteit: standaard REST endpoint (laag hallucinatie-risico)
├── Token budget: ~50K tokens (sonnet)
├── File contention: routes.py wordt ook geraakt door story 1.1.3
└── Geschatte kosten: $0.15
```

**Vuistregel voor optimale story-grootte voor LLM agents:**
- **Context radius <= 8 files** — meer dan 8 en de agent raakt context kwijt
- **Wijziging scope <= 4 files** — meer en de kans op inconsistentie stijgt
- **Eén duidelijk doel** — "maak X die Y doet zodat Z" in één zin
- **AC's verifieerbaar met code** — geen "het voelt goed" maar "GET /auth retourneert 200 met token"

Te klein: "Voeg een import toe" — overhead van sessie-start > waarde
Te groot: "Bouw het hele auth systeem" — hallucinatie, context-verlies, niet auditeerbaar

**Sweet spot: een story die in 1 sessie van 15-30 minuten door de agent gebouwd kan worden, 2-4 files raakt, en 3-5 testbare AC's heeft.**

### 2. Definition of Done per niveau

Je noemt AC's maar niet een formele Definition of Done (DoD). Voor LLM-agents is dit cruciaal omdat de agent letterlijk checkt: "voldoe ik aan de criteria?"

```
Epic DoD:
- Alle features in de epic zijn Done
- Integratie tussen features getest
- Geen regressies in andere epics

Feature DoD:
- Alle user stories in de feature zijn Done
- Feature-level integratietest passed
- Geen mock/fake data in productie code
- Code review door review agent goedgekeurd

User Story DoD:
- Alle AC's verifieerbaar met automated tests
- Lint + type-check passed
- Geen nieuwe warnings geintroduceerd
- Tests geschreven EN passing
- Git commit met traceerbaarheid naar story ID
```

**Waarom dit ertoe doet**: De coding agent markeert nu een feature als "passing" wanneer HIJ denkt dat het klaar is. Met een formele DoD checkt de orchestrator (of deterministische nodes) objectief of het echt klaar is.

### 3. Traceerbaarheid: story -> code -> test -> verificatie

Je zegt "auditeerbaar". Dat vereist een traceerbaarheidsmatrix:

```
User Story 1.1.2: "Auth endpoint"
├── Code wijzigingen:
│   ├── src/routes/auth.py  (regel 45-89)   ← git blame -> story 1.1.2
│   └── tests/test_auth.py  (regel 12-67)   ← git blame -> story 1.1.2
├── Tests:
│   ├── test_login_returns_token      PASSED
│   ├── test_invalid_creds_returns_401 PASSED
│   └── test_expired_token_rejected    PASSED
├── Verificatie:
│   ├── Lint:         PASSED (deterministic)
│   ├── Mock check:   PASSED (deterministic)
│   ├── Type check:   PASSED (deterministic)
│   └── Review agent: APPROVED (LLM)
└── Tijdlijn:
    ├── 14:32 Agent "Spark" claimed story
    ├── 14:33 Read 4 files (context gathering)
    ├── 14:35 Wrote auth.py endpoint
    ├── 14:38 Wrote test_auth.py
    ├── 14:40 Ran tests: 3/3 passed
    ├── 14:41 Lint: passed
    ├── 14:41 Mock check: passed
    ├── 14:42 Git commit: "feat(auth): add login endpoint [story-1.1.2]"
    └── 14:43 Marked as passing
```

**Wat DevEngine nu mist**:
- Git commits zijn niet gelinkt aan story ID's (de agent commit als hij wil, niet per story)
- Test results zijn niet gekoppeld aan specifieke AC's
- Er is geen audit trail per story — alleen raw logs

### 4. Regressie-detectie tussen stories

Story B implementeren kan story A breken. Nu detecteert de testing agent dit achteraf. Maar:

- **Wanneer** wordt de regressie gedetecteerd? Soms pas na 5 stories verder.
- **Wie** fixt het? De coding agent die story B maakte? Of een nieuwe agent?
- **Hoe** voorkomen we het? Door stories met file contention sequentieel te plannen.

**Wat je nodig hebt**:
- Na elke story: draai ALLE tests (niet alleen van die story) als deterministic check
- File contention detectie in de story planner: "story 1.1.2 en 1.1.3 raken beide routes.py — maak ze sequentieel"
- Snelle regressie feedback: als story B een test van story A breekt, direct melden

### 5. Kennis-accumulatie tussen stories

Story 1.1.1 bouwt de database. Story 1.1.2 bouwt de API erop. De agent van story 1.1.2 moet WETEN wat 1.1.1 heeft gebouwd — niet door de hele codebase te verkennen maar door gestructureerde kennis.

**Nu**: De memory MCP tools (memory_store/memory_recall) bestaan maar worden inconsistent gebruikt. De agent van story 1.1.2 moet zelf bedenken om architecture memory op te halen.

**Nodig**: Automatische context-injectie per story:
```
Voordat de agent aan story 1.1.2 begint, krijgt hij:
- Architecture decisions (uit memory)
- Wat story 1.1.1 heeft gebouwd: "Database tabel 'sessions' met kolommen id, user_id, token, expires_at"
- Welke files story 1.1.1 heeft aangemaakt/gewijzigd
- Relevante test results van story 1.1.1
```

Dit is NIET hetzelfde als de hele codebase verkennen. Het is een gestructureerde briefing.

### 6. Human review gates — op welk niveau?

Je zegt auditeerbaar. Maar wanneer kijkt een mens mee?

| Niveau | Review gate | Doel |
|---|---|---|
| Per user story | Optioneel — alleen bij "needs_human_review" escalatie | Blokkerende issues |
| Per feature | Aanbevolen — diff review na alle stories in feature klaar | Samenhang controleren |
| Per sprint | Verplicht — sprint review/demo | Stakeholder alignment |

**Nu**: DevEngine heeft stuck-state recovery (human intervention bij problemen) en de review agent. Maar er is geen formeel sprint review moment.

### 7. Rollback strategie

Wat als een story-implementatie zo slecht is dat het niet te fixen is?

**Nu**: De feature gaat terug naar "failing" en de coding agent probeert opnieuw. Maar er is geen rollback naar de staat VOOR die story.

**Nodig**: Git-gebaseerde rollback:
- Elke story begint met een git tag/bookmark
- Als de story na N retries faalt, `git reset` naar de bookmark
- De story wordt als "blocked" gemarkeerd voor menselijke interventie

### 8. Technische schuld tracking

LLM-gegenereerde code accumuleert technical debt:
- Copy-paste patronen (agent hergebruikt niet altijd bestaande utilities)
- Inconsistente naming conventions
- Overtollige dependencies
- Ontbrekende error handling op edge cases

**Nodig**: Een periodieke "tech debt" sweep — per sprint of per epic — waar een agent specifiek kijkt naar:
- Duplicatie detectie
- Ongebruikte code
- Inconsistente patronen
- Missing error handling

### 9. Integratie-testing op feature-niveau

Individuele stories passen hun eigen tests. Maar werken de stories samen?

```
Story 1.1.1: Database tabel      ✓ (eigen tests passing)
Story 1.1.2: Auth endpoint       ✓ (eigen tests passing)
Story 1.1.3: JWT tokens          ✓ (eigen tests passing)

Feature 1.1: Login flow          ? (integratietest?)
```

**Nu**: Er is geen feature-level integratietest. De testing agent test individuele stories.

**Nodig**: Na alle stories in een feature, een integratietest die de hele flow test (login -> token -> authenticated request -> logout).

### 10. Kosten-transparantie per story/feature/sprint

Je zegt "kosten afwegen tegen kwaliteit". Dan moet je de kosten ZIEN:

```
Sprint 3 — Kosten overzicht:
├── Epic 1: User Management        $4.20
│   ├── Feature 1.1: Login flow    $2.80
│   │   ├── Story 1.1.1: DB       $0.45  (haiku: explore, sonnet: implement)
│   │   ├── Story 1.1.2: Auth     $0.95  (sonnet: implement, retry: 1)
│   │   ├── Story 1.1.3: JWT      $0.60  (sonnet: implement)
│   │   └── Integration test      $0.80  (testing agent)
│   └── Feature 1.2: Registration $1.40
│       └── ...
├── Deterministic checks           $0.00  (geen tokens)
├── Review agents                  $1.20
└── TOTAAL                         $5.40

Kwaliteitsmetrieken:
├── Stories first-pass success:    14/18  (78%)
├── Retries nodig:                 4 stories
├── Regressies gedetecteerd:       2
├── Human interventies:            1
└── Token efficiency:              $0.30/story gemiddeld
```

**Nu**: DevEngine trackt geen token-kosten. Er is geen inzicht in wat een feature kost.

---

## Samenvatting: wat mist er

| # | Ontbrekend puzzelstuk | Impact | Moeilijkheid |
|---|---|---|---|
| 1 | LLM-specifiek sizing model (niet story points) | Voorkomt hallucinatie, optimaliseert kosten | Medium — story planner aanpassen |
| 2 | Definition of Done per niveau | Objectieve "klaar" criteria, niet agent's oordeel | Laag — prompt + deterministic checks |
| 3 | Traceerbaarheid story -> code -> test | Auditeerbaar, navolgbaar | Medium — git commit linking + test mapping |
| 4 | Regressie-detectie tussen stories | Voorkomt dat story B story A breekt | Medium — full test suite als post-check |
| 5 | Kennis-accumulatie (gestructureerde briefing) | Betere context = minder hallucinatie | Medium — automatische context-injectie |
| 6 | Human review gates op juiste niveaus | Kwaliteitsborging zonder bottleneck | Laag — configuratie |
| 7 | Git-gebaseerde rollback per story | Vangnet bij fatale fouten | Medium — git tag/reset mechanisme |
| 8 | Tech debt tracking | Voorkomt code-rot over sprints | Laag — periodieke analyse-agent |
| 9 | Feature-level integratietest | Test samenhang, niet alleen onderdelen | Hoog — test generatie |
| 10 | Kosten-transparantie per story | Informed decision making | Medium — token tracking + UI |

---

## Hoe dit het v2 plan beinvloedt

De 10 punten hierboven zijn grotendeels ONAFHANKELIJK van de workflow engine discussie. Ze gaan over het PROCES, niet de EXECUTIE-ARCHITECTUUR.

Of we nu kiezen voor:
- **Optie A** (post-checks in orchestrator) of
- **Optie B** (volledige workflow engine)

...deze 10 punten moeten in beide gevallen geadresseerd worden.

Dit verschuift de prioriteit: misschien is de workflow engine niet het EERSTE dat v2 nodig heeft. Misschien is het:

1. Hierarchie formaliseren (Epic -> Feature -> Story met DoD per niveau)
2. Traceerbaarheid inbouwen (story ID -> git commit -> test results)
3. Deterministische post-checks (lint, test, mock, regressie)
4. LLM sizing model (story planner + context radius)
5. Kosten-tracking
6. DAN pas: workflow engine voor fijnmazige controle over het executieproces
