# AutoForge Roadmap

> Transformatie van een waterval-gebaseerde code generator naar een iteratief, agile development platform met multi-model ondersteuning.

---

## Fase 0: Development Aanpak — Bootstrap Protocol

**Doel:** AutoForge incrementeel ombouwen met dezelfde agile principes die we aan het bouwen zijn. We "practice what we preach" door sprints handmatig te managen totdat het systeem zichzelf kan aansturen.

### 0.1 Bootstrap Paradox

We bouwen een agile sprint-systeem, maar dat systeem bestaat nog niet. Daarom:

- **Nu:** Claude Code (AI-assistent) fungeert als sprint manager. Kent de end-state (deze roadmap), de huidige staat (codebase), en bepaalt samen met de gebruiker welke kleine blokjes in de volgende sprint gaan.
- **Straks:** Zodra het sprint-systeem werkend is (einde Fase 2+3), migreren we het beheer naar AutoForge zelf. AutoForge managed dan zijn eigen doorontwikkeling.

```
Bootstrap fase (Fase 0-3):
  Gebruiker + Claude Code = handmatige sprint planning
  AutoForge = het product dat gebouwd wordt
                    ↓
Self-hosting fase (na Fase 3):
  Gebruiker + AutoForge = geautomatiseerde sprint planning
  AutoForge = zowel het product als de bouwer
```

### 0.2 Sprint Spelregels

Elke sprint volgt dit protocol:

**1. Planning (Claude Code + gebruiker)**
- Claude Code stelt de sprint inhoud voor op basis van de roadmap
- Gebruiker keurt goed, past aan, of voegt toe
- Scope: klein genoeg dat AutoForge na de sprint nog steeds draait

**2. Uitvoering**
- Kleine, gerichte wijzigingen — één concern per commit
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

### 0.3 Veiligheidsprotocol

| Regel | Waarom |
|---|---|
| Git commit na elke werkende wijziging | Rollback altijd mogelijk |
| Git push na elke sprint | Remote backup, samenwerking |
| Nooit agent.py + client.py + MCP server tegelijk wijzigen | Beperkt blast radius als iets breekt |
| Nieuwe code naast bestaande code, niet eroverheen | Bestaande functionaliteit blijft werken |
| Feature flags voor grote wijzigingen | Nieuwe flow aan/uit te zetten zonder code revert |

### 0.4 Sprint Backlog (door Claude Code beheerd)

Claude Code houdt de sprint backlog bij in dit document. Na elke sprint wordt de status bijgewerkt.

#### Sprint 1: OpenRouter Multi-Model Support (Fase 4) — DONE
> Laagste risico, hoogste onafhankelijkheid. Raakt geen bestaande kernlogica.
> Afgerond: 2026-02-06 — Commit `d0a3e83`

| # | Item | Status |
|---|---|---|
| 1.1 | Per agent-type model configuratie in registry/settings | done |
| 1.2 | API schema's uitbreiden (model per agent-type in start request) | done |
| 1.3 | Process manager: juiste model doorgeven per agent subprocess | done |
| 1.4 | Orchestrator: per-type model routing naar coding/testing/initializer | done |
| 1.5 | UI: model selectie per agent-type op settings pagina (incl. custom input) | done |
| 1.6 | Model validatie gerelaxed: accepteert OpenRouter/Ollama/GLM model IDs | done |
| 1.7 | Documentatie: OpenRouter setup in README | pending |

#### Sprint 2: Data Model Fundament (Fase 1)
> Nieuwe tabellen toevoegen naast bestaande Feature tabel. Additief, geen breaking changes.

| # | Item | Status |
|---|---|---|
| 2.1 | Epic tabel toevoegen aan database.py | pending |
| 2.2 | UserStory tabel toevoegen (met story_points, function_points) | pending |
| 2.3 | AcceptanceCriteria tabel toevoegen | pending |
| 2.4 | Sprint tabel toevoegen | pending |
| 2.5 | SprintRetrospective tabel toevoegen | pending |
| 2.6 | Relaties leggen (epic → feature → story → criteria) | pending |
| 2.7 | Migratiescript: bestaande features koppelen aan auto-epic | pending |
| 2.8 | MCP server uitbreiden met epic/story/sprint tools | pending |

#### Sprint 3: Analyse Workflow (Fase 2.1-2.2)
> Analyse agent en sprint planning — kern van de agile transformatie.

| # | Item | Status |
|---|---|---|
| 3.1 | Analyse agent prompt template | pending |
| 3.2 | Epic → Feature → Story opsplitsingslogica | pending |
| 3.3 | Story point schatting door AI | pending |
| 3.4 | Acceptatiecriteria generatie (functional + non-functional) | pending |
| 3.5 | Sprint planning agent: story selectie op basis van prioriteit + dependencies | pending |
| 3.6 | Sprint planning API endpoints | pending |

#### Sprint 4: Sprint Uitvoering & DoD (Fase 2.3-2.5)
> Coding agent werkt per sprint, DoD checks, retrospective.

| # | Item | Status |
|---|---|---|
| 4.1 | Sprint-based coding agent flow (werk alleen sprint items af) | pending |
| 4.2 | DoD checks per story (acceptatiecriteria, regression, lint) | pending |
| 4.3 | Sprint completion detectie | pending |
| 4.4 | Retrospective agent: evaluatie + learnings opslaan | pending |
| 4.5 | Git tag per sprint | pending |

#### Sprint 5: Dual Kanban Board UI (Fase 3)
> Visuele laag bovenop de workflow engine.

| # | Item | Status |
|---|---|---|
| 5.1 | Analyse Board component (Inbox → In Analyse → Ready) | pending |
| 5.2 | Sprint Board component (To Do → In Progress → Testing → Done) | pending |
| 5.3 | Sprint selector en historische sprints | pending |
| 5.4 | Epic/Feature/Story drill-down views | pending |
| 5.5 | Drag & drop prioritering | pending |

#### Sprint 6: Velocity & Metrics (Fase 5)
> Data-gedreven planning.

| # | Item | Status |
|---|---|---|
| 6.1 | Story point tracking per sprint (planned vs actual) | pending |
| 6.2 | Velocity berekening (rolling average) | pending |
| 6.3 | Burn-down chart component | pending |
| 6.4 | Schattingsnauwkeurigheid tracking | pending |
| 6.5 | Dashboard met project metrics | pending |

#### Sprint 7: Continuous Delivery & Self-Hosting (Fase 6 + Bootstrap Exit)
> Release management + AutoForge managed zichzelf.

| # | Item | Status |
|---|---|---|
| 7.1 | Automatische git tag/release na sprint | pending |
| 7.2 | Release notes generatie | pending |
| 7.3 | Volledige regression suite per sprint | pending |
| 7.4 | Migratie: AutoForge eigen backlog importeren in het systeem | pending |
| 7.5 | Self-hosting: AutoForge managed eigen doorontwikkeling | pending |

### 0.5 Hoe een sprint te starten

De gebruiker vraagt Claude Code om de volgende sprint te starten. Claude Code:

1. Leest deze roadmap en de huidige codebase
2. Presenteert de sprint items aan de gebruiker
3. Na goedkeuring: voert de items één voor één uit
4. Na elk item: commit, verifieer dat AutoForge werkt
5. Na alle items: push, sprint review met gebruiker
6. Werkt de status in deze roadmap bij

**Commando:** Gebruiker zegt: _"Start sprint [nummer]"_ of _"Wat is de volgende sprint?"_

---

## Visie

AutoForge evolueert naar een platform dat software bouwt in **agile/scrum sprint-cycli**, waarbij elke sprint werkende, bruikbare software oplevert. De gebruiker en AI werken samen aan analyse, planning en realisatie. Het huidige "alles-in-een-keer" model wordt vervangen door een iteratief proces met twee kanban boards: een **analyse board** en een **sprint board**.

Door integratie met OpenRouter krijgt AutoForge toegang tot 400+ AI-modellen, waarbij per agent-type het optimale model ingezet kan worden.

---

## Fase 1: Data Model & Architectuur

**Doel:** Het fundament leggen voor agile werkwijzen door het datamodel uit te breiden van een platte feature-lijst naar een volledige projecthierarchie.

### 1.1 Hiërarchisch backlog model

Huidige situatie: alleen een `Feature` tabel.

Nieuwe structuur:

```
Epic
 └── Feature
      └── UserStory
           └── AcceptanceCriteria
```

| Entiteit | Doel | Key velden |
|---|---|---|
| **Epic** | Groot functioneel blok (bv. "Authenticatie systeem") | naam, beschrijving, prioriteit, status, eigenaar (user/AI) |
| **Feature** | Concrete functionaliteit binnen een epic (bv. "Login met email") | naam, beschrijving, epic_id, status, dependencies |
| **UserStory** | Implementeerbare eenheid met testbare criteria (bv. "Als gebruiker wil ik mijn wachtwoord resetten") | beschrijving, feature_id, story_points, function_points, status, sprint_id |
| **AcceptanceCriteria** | Testbaar criterium per story (user-defined + non-functional) | beschrijving, type (functional/non-functional), user_story_id, status |

### 1.2 Sprint model

| Entiteit | Doel | Key velden |
|---|---|---|
| **Sprint** | Een iteratiecyclus met een selectie van stories | nummer, doel, status (planning/active/review/done), velocity_planned, velocity_actual |
| **SprintRetrospective** | Evaluatie na afloop van een sprint | sprint_id, wat_ging_goed, wat_kan_beter, ai_learnings |

### 1.3 Non-functional requirements

Generieke kwaliteitseisen die op alle stories van toepassing zijn:

- Worden projectbreed gedefinieerd (bv. "alle endpoints moeten rate limiting hebben")
- Worden automatisch als acceptatiecriteria toegevoegd aan relevante stories
- Categorieën: performance, security, accessibility, maintainability, etc.

### 1.4 Migratie

- Bestaande `Feature` records migreren naar de nieuwe structuur
- Backward-compatible: bestaande projecten blijven werken
- Migratiepad: huidige features worden stories onder een auto-gegenereerde epic

---

## Fase 2: Agile Workflow Engine

**Doel:** Het hart van het nieuwe systeem — de motor die analyse, planning en uitvoering in sprint-cycli aanstuurt.

### 2.1 Analyse fase (Backlog Refinement)

De analyse agent breekt werk op in implementeerbare eenheden:

```
Input (app_spec / epic / feature request / bug report)
  ↓
Analyse agent scant bestaande codebase & feature DB
  ↓
Opsplitsing: Epic → Features → User Stories
  ↓
Story points & function points schatting
  ↓
Acceptatiecriteria genereren (functional + non-functional)
  ↓
Items op Analyse Board → status "Ready for Sprint"
```

**Backlog vulling door twee partijen:**
- **Gebruiker:** weet wat hij wil bouwen, kan epics/features/bugs toevoegen
- **AI:** kent patronen van dit type applicatie, stelt ontbrekende features voor (bv. "je hebt auth maar mist rate limiting"), identificeert technische schuld

**Analyse is altijd incrementeel:** gebaseerd op wat er al gerealiseerd is (feature DB + codebase), niet op een volledig vooraf uitgewerkt plan.

### 2.2 Sprint Planning

Samenwerking tussen AI en gebruiker:

1. **AI stelt voor:** selecteert stories uit "Ready for Sprint" op basis van:
   - Prioriteit (gebruiker-bepaald)
   - Dependencies (wat moet eerst)
   - Velocity (hoeveel story points passen in een sprint, gebaseerd op historische data)
   - Samenhang (stories die logisch bij elkaar horen)
2. **Gebruiker keurt goed:** past selectie aan, voegt toe, verwijdert
3. **Sprint start:** geselecteerde stories gaan naar het Sprint Board

### 2.3 Sprint Uitvoering

De coding agent werkt stories af volgens het Sprint Board:

- Pakt stories op basis van prioriteit en dependencies
- Elke story moet door de Definition of Done
- Applicatie blijft werkend na elke afgeronde story
- Bij blokkades: story terug naar backlog, volgende oppakken

### 2.4 Definition of Done

**Per User Story:**
- Alle acceptatiecriteria passing (geautomatiseerde tests)
- Non-functional requirements voldaan
- Geen nieuwe lint/type fouten
- Integreert met bestaande functionaliteit
- Code gecommit

**Per Sprint:**
- Alle sprint-items op "done" (of bewust teruggeschoven naar backlog)
- Applicatie bouwt, start, en is bruikbaar
- Geen regressies op eerder opgeleverde features (regression tests)
- Git tag/release voor de sprint
- Gebruiker kan testen en feedback geven

Items die niet door DoD komen gaan terug naar de product backlog voor de volgende sprint.

### 2.5 Sprint Review & Retrospective

**Review:**
- Gebruiker test de opgeleverde versie
- Feedback leidt tot nieuwe backlog items (bugs, verbeteringen, nieuwe wensen)

**Retrospective (AI-gedreven):**
- Wat ging goed deze sprint?
- Wat kan beter?
- Schatting-nauwkeurigheid: vergelijk geschatte vs. werkelijke story points
- Learnings opslaan voor toekomstige sprints (bv. "API-integratie stories kosten meer punten dan geschat")

### 2.6 Uniforme intake voor alle werktypen

Alle typen werk volgen hetzelfde proces:

| Type | Intake | Prioriteit |
|---|---|---|
| Nieuwe feature | Epic/feature op product backlog | Gebruiker bepaalt |
| Feature request | Story of feature op backlog | Gebruiker bepaalt |
| Bug (productie) | Story op backlog met hoge prioriteit | Hoog (was al in productie) |
| Maintenance | Story op backlog | Gebruiker bepaalt |
| Technische schuld | AI stelt voor, gebruiker prioriteert | Gebruiker bepaalt |

---

## Fase 3: Dual Kanban Board UI

**Doel:** Twee overzichtelijke boards die de volledige workflow visualiseren.

### 3.1 Analyse Board (Product Backlog)

Kolommen:
| Kolom | Inhoud |
|---|---|
| **Inbox** | Nieuwe epics, feature requests, bugs (van gebruiker of AI) |
| **In Analyse** | Wordt opgesplitst in features/stories door de analyse agent |
| **Ready for Sprint** | Volledig uitgeanalyseerd, story points geschat, acceptatiecriteria gedefinieerd |

Functionaliteit:
- Drag & drop voor prioritering
- Filteren op type (epic/feature/bug/maintenance)
- Epic → Feature → Story drill-down
- Story point totalen per kolom
- AI-suggesties markering (voorgesteld door AI vs. toegevoegd door gebruiker)

### 3.2 Sprint Board

Kolommen:
| Kolom | Inhoud |
|---|---|
| **To Do** | Sprint items die nog opgepakt moeten worden |
| **In Progress** | Wordt gebouwd door de coding agent |
| **Testing** | Wordt geverifieerd (DoD check, regression tests) |
| **Done** | Passing, opgeleverd |

Functionaliteit:
- Sprint selector (huidige + historische sprints)
- Burn-down chart (story points resterend over tijd)
- Velocity grafiek (story points per sprint, historisch)
- Real-time agent output streaming (bestaande functionaliteit)
- Sprint goal weergave

### 3.3 Gedeelde UI elementen

- Dashboard met project metrics (velocity, totale voortgang, burn-down)
- Story detail view (acceptatiecriteria, non-functional requirements, status, test resultaten)
- Epic progress view (welke features/stories klaar, in progress, nog te doen)
- Notificaties voor AI-suggesties en sprint events

---

## Fase 4: Multi-Model Support via OpenRouter

**Doel:** Maximale flexibiliteit en kostenoptimalisatie door per agent-type het optimale model in te zetten.

### 4.1 OpenRouter integratie

- Configuratie via `.env` / `autoforge config`:
  ```
  ANTHROPIC_BASE_URL=https://openrouter.ai/api
  ANTHROPIC_AUTH_TOKEN=<openrouter-api-key>
  ```
- Toegang tot 400+ modellen (Claude, GPT, Gemini, Llama, Mistral, etc.)
- Geen Anthropic-abonnement vereist
- Automatische failover tussen providers

### 4.2 Per agent-type model selectie

| Agent Type | Taak | Aanbevolen model-profiel |
|---|---|---|
| **Analyse agent** | Epics opsplitsen, stories schrijven, acceptatiecriteria | Sterk in planning & architectuur |
| **Sprint planning agent** | Story selectie, capaciteitsplanning | Sterk in redeneren & prioriteren |
| **Coding agent** | Implementatie van user stories | Sterk in code generatie |
| **Testing agent** | Regression tests, DoD verificatie | Snel en kostenefficiënt |
| **Retrospective agent** | Sprint evaluatie, learnings | Sterk in analyse & reflectie |

Configuratie in UI:
- Settings pagina met model dropdown per agent-type
- Presets (bv. "Budget", "Balanced", "Premium")
- Kostenindicatie per configuratie (op basis van OpenRouter pricing)

### 4.3 Data model uitbreiding

- Model keuze per agent-type opslaan in project settings of globale settings
- API schema's uitbreiden voor per-agent model configuratie
- Process manager routeert het juiste model naar elk agent subprocess

---

## Fase 5: Velocity & Metrics

**Doel:** Data-gedreven sprint planning door het bijhouden en analyseren van velocity en schattingsnauwkeurigheid.

### 5.1 Story Point Tracking

- Story points per user story (geschat door AI, aanpasbaar door gebruiker)
- Function points per user story (objectieve maat voor omvang)
- Planned vs. actual per sprint
- Cumulatieve tracking over alle sprints

### 5.2 Velocity berekening

- Velocity = opgeleverde story points per sprint
- Rolling average over laatste 3-5 sprints
- Gebruikt voor sprint capaciteitsplanning: "Op basis van velocity passen er ~X story points in de volgende sprint"

### 5.3 Schattingsnauwkeurigheid

- Per sprint: vergelijk geschatte vs. werkelijke effort
- Trendanalyse: wordt de AI beter in schatten over tijd?
- Categorieën: overschat, onderschat, accuraat
- Learnings meenemen in volgende schattingen (retrospective data)

### 5.4 Dashboards

- Velocity trend grafiek
- Burn-down chart per sprint
- Cumulatieve flow diagram (product backlog)
- Story point verdeling per type (feature/bug/maintenance)
- Schattingsnauwkeurigheid over tijd

---

## Fase 6: Continuous Delivery per Sprint

**Doel:** Elke sprint resulteert in een werkende, deploybare applicatie.

### 6.1 Release management

- Automatische git tag na succesvolle sprint (bv. `sprint-3-v0.3.0`)
- Release notes generatie (op basis van opgeleverde stories)
- Build verificatie (applicatie start succesvol)

### 6.2 Regression testing

- Na elke story: regression tests op eerder opgeleverde features
- Na sprint completion: volledige regression suite
- Bij regressie: story terug naar sprint board of volgende sprint

### 6.3 Dependency management

- Dependencies tussen stories worden gerespecteerd bij sprint planning
- AI bouwt niet aan stories waarvan dependencies nog niet gerealiseerd zijn
- Dependency visualisatie in de UI (graaf)

---

## Implementatie Volgorde

```
Fase 1 ──→ Fase 2 ──→ Fase 3
  Data       Workflow    UI
  Model      Engine      Boards

              Fase 4 (parallel, onafhankelijk)
              Multi-Model / OpenRouter

                    Fase 5 ──→ Fase 6
                    Metrics    Continuous
                               Delivery
```

| Fase | Afhankelijk van | Prioriteit |
|---|---|---|
| 1. Data Model | - | Fundament, moet eerst |
| 2. Agile Workflow | Fase 1 | Kern van de transformatie |
| 3. Dual Kanban UI | Fase 1 + 2 | Gebruikerservaring |
| 4. Multi-Model / OpenRouter | Onafhankelijk | Kan parallel aan fase 1-3 |
| 5. Velocity & Metrics | Fase 2 | Na eerste sprints met data |
| 6. Continuous Delivery | Fase 2 | Na stabiele workflow |

---

## Open Punten

- [ ] Exacte sprint-grootte definitie: story points capaciteit per sprint (leert het systeem dit zelf via velocity?)
- [ ] MCP server uitbreiding: nieuwe tools voor epic/story/sprint management naast bestaande feature tools
- [ ] Prompt templates: nieuwe prompts voor analyse agent, sprint planning agent, retrospective agent
- [ ] Migratie strategie: hoe converteren we bestaande projecten naar het nieuwe model?
- [ ] UI/UX design: wireframes voor de twee kanban boards en dashboard
