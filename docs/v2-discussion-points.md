# DevEngine v2 — Discussiepunten & Afwegingen

Status: Bijgewerkt na sparring-sessie 2026-04-10

---

## BESLOTEN

| # | Beslissing | Keuze | Reden |
|---|---|---|---|
| D1 | mq-planning mapping | Module=Epic, Cycle=Sprint, Issue=Feature/Story | Native Plane concepten |
| D2 | Alleen stories hebben AC's | Ja | Features/epics zijn containers |
| D3 | DevEngine kent geen epics/features | Ja, bouwt alleen stories | mq-planning beheert hierarchie |
| D4 | Taken leven in DevEngine | Ja, niet in mq-planning | Technisch, vluchtig, intern |
| D5 | UI: stepper + accordeon | Ja | Drie niveaus: AC's → taken → tool-calls |
| D6 | Deterministic checks: alles | Lint + test + mock-check + server-restart | Agent kan niet overslaan |
| D7 | Input-kwaliteit in PO-Companion | Ja, niet in DevEngine | Sparring + gates + PO validatie |
| D8 | DevEngine triggert mq-testing | Story done → module, Feature done → integratie+e2e+UI | DevEngine weet wanneer |
| D9 | planning_sync meenemen | Ja in v2 scope | Maar niet als blocker |
| D10 | Feature.steps → acceptance_criteria | Ja | Correcte terminologie |
| D11 | Feature.tasks → verdwijnt | Ja, sub-features zijn aparte records | Eén mechanisme |
| D12 | v1 afsluiting | Merge alles naar master, tag v1.0.0 | Clean break |
| D13 | Mega-sessie + post-checks | Mega-sessie behouden, multi-sessie naar v3 | Overhead te hoog |
| D14 | Post-checks in orchestrator | Geen workflow engine, post-checks als module | 80% voordeel, 20% complexiteit |
| D15 | Git commit per story | Orchestrator doet de commit (deterministic) | Agent kan het niet vergeten |
| D16 | Review agent blijft | Code kwaliteit/security. mq-testing doet functioneel | Twee verschillende brillen |
| D17 | Feature tabel rename OK | Naar "Story" of behoud met level kolom | Bij v2, breaking change |
| D18 | v2 is breaking change | Geen backward compatibility | Clean break, migratiescript |
| D19 | Testing agent + mq-testing | Testing agent = DevEngine intern (smoke/regressie). mq-testing = extern (herhaalbaar, feature-level) | Complementair |
| D20 | mq-testing rapporteert aan PO-Companion | Compleet testoverzicht per feature/sprint in PO-Companion | PO ziet alles in één plek |
| D21 | Feature test failure = human in the loop | Via PO-Companion, PO beslist next action | Niet automatisch retry |
| D22 | Verificatie-volgorde in UI | AC's → E2E/UI → Tests → Lint → Mock → Regressie → Review → PO | Van belangrijk naar minder belangrijk |
| D23 | Codex als reviewer | Codex VERVANGT review agent. Reviewed code met AC's + tech stack + story context | Ander model = onafhankelijke review |
| D24 | DoD is harde eis | Story/feature mag pas "done" als DoD volledig voldaan | Geen self-reporting door agent |
| D25 | Mock data moet opgelost | Deterministic grep + reviewer checkt | #1 kwaliteitsprobleem |
| D26 | Story ↔ git commit relatie | Orchestrator legt relatie, commit per story met ID | Traceerbaarheid |
| D27 | Token-kosten tracking | Moet uitgezokt worden (SDK of proxy) | Onderzoekspunt |
| D28 | Geen YOLO mode in v2 | YOLO verdwijnt, standaard flow is altijd met checks | Kwaliteit boven snelheid |
| D29 | Tests structureel hoge kwaliteit | Testing agent + mq-testing + deterministic. Geen optioneel | Kwaliteit is niet onderhandelbaar |
| D30 | Review agent standaard aan | Geen feature flag, altijd actief | Was optioneel, wordt verplicht |
| D31 | mq-wiki als brug PO-Companion → DevEngine | Wiki bewaart arch.md/prd.md, DevEngine leest via wiki API | SSOT voor project-definitie |
| D32 | Codex reject → retry | Max 3 tries, kosten geteld, daarna human in the loop | Consistent met retry strategie |
| D33 | Test kwaliteit = coverage | >= 80% van gewijzigde regels + AC validatie via mq-testing | Coverage structureel, mq-testing functioneel |
| D34 | DoD opzet goedgekeurd | Generiek + project-specifiek via checks.yaml | Zie DEEL VI analyse document |
| D35 | End-to-end flow goedgekeurd | 10 fasen: definitie → sprint → decompositie → bouw → checks → review → commit → module test → feature test → sprint review | Zie DEEL VII analyse document |
| D36 | Orchestrator: eerst ernaast, dan refactoren | Post-checks als module ernaast. Werkend → werkend → werkend. Pas refactoren als het draait | Eén stap tegelijk, problemen isoleerbaar |
| D37 | checks.yaml: samen bespreken wat erin komt | Per check: nuttig/noodzakelijk/gevaarlijk/onnodig. PO maakt keuze, bijstelbaar gaandeweg | Geen vaste lijst, evolueert |
| D38 | Feature tabel hernoemen naar Story | Ja, rename bij v2 | Consistent met terminologie |
| D39 | checks.yaml indeling | Noodzakelijk (altijd aan): lint, type-check, mock, regressie, coverage, git commit. Nuttig (per project): server-restart, API contract, accessibility, bundle size. Gevaarlijk: security scan (false positives) | PO beslist per project, bijstelbaar |
| D40 | Load testing op feature + sprint niveau | Per feature: lichte load test (alleen die feature's endpoints). Per sprint: volledige load test. Per story: geen. | mq-testing voert uit bij feature completion en sprint completion |
| D41 | mq-wiki = geindexeerde kennislaag | Systemen pushen content, wiki bewaart + genereert help + serveert via API. Per project een wiki-domein | Hybride rol: niet alleen opslag, ook content-generatie |
| D42 | Help-content generatie event-driven | Bij feature done, bug aangemaakt/opgelost, sprint done. Wiki genereert uit AC's + screenshots + bugs | Niet periodiek, niet handmatig |
| D43 | Support overlay gefaseerd | Fase 1 (v2): statische help pages. Fase 2 (v2.1): FAQ + zoek in wiki. Fase 3 (v3): RAG chatbot als embedbare widget | Incrementeel, pas RAG bij >=75% coverage |

---

## OPEN — Architectuur

### A4. Orchestrator refactoring
- **Status**: OPEN
- **Vraag**: parallel_orchestrator.py is 3259 regels. Refactoren voor v2 of laten?
- **Optie A**: Eerst refactoren naar <1500 regels, dan v2 features toevoegen
- **Optie B**: Minimale wijzigingen, post-checks als aparte module ernaast
- **Risico**: Zonder refactoring groeit het bestand verder
- **Conclusie**: —

### A5. YAML checks.yaml scope
- **Status**: OPEN
- **Vraag**: Welke deterministic checks zijn configureerbaar per project via `checks.yaml`?
- **Default aan**: lint, type-check, mock-check, regressie suite
- **Optioneel**: server-restart test, custom project-specifieke checks
- **Conclusie**: —

---

## OPEN — Pipeline integratie

### P1. Gap PO-Companion → DevEngine: architecturale context
- **Status**: OPEN — meer uitleg nodig voor beslissing
- **Vraag**: Tech stack, schema, API contract staan in PO-Companion's arch.md maar komen niet mee via mq-planning. Hoe komt dit bij DevEngine?
- **Optie A**: PO-Companion genereert app_spec.txt en commit in project Git repo
- **Optie B**: DevEngine leest arch.md direct uit project Git
- **Optie C**: Via PO-Companion API endpoint
- **Optie D**: Via mq-wiki API
- **Context**: Zie DEEL VI van v2-analysis.md voor wiki-opties
- **Conclusie**: —

### P3. PO-Companion portfolio view
- **Status**: BESLOTEN — ja, bouwen in PO-Companion
- **Vraag**: Welke bronnen leest PO-Companion?
- **Voorstel**: mq-planning (status) + DevEngine API (voortgang, kosten) + mq-testing API (test resultaten)
- **Conclusie**: —

---

## OPEN — DevEngine intern

### I2. Token-kosten tracking
- **Status**: OPEN — onderzoek nodig
- **Vraag**: Hoe tracken we kosten per story/feature/sprint?
- **Open actie**: Onderzoek of Claude Agent SDK usage stats teruggeeft
- **Fallback**: Schatting op basis van prompt/response lengte
- **Conclusie**: —

### I5. Feature tabel hernoemen
- **Status**: OPEN — rename is OK (D17), maar naar wat?
- **Optie A**: Hernoem naar "Story" (consequent met terminologie)
- **Optie B**: Behoud "Feature" tabel, voeg `level` kolom toe
- **Vraag**: Hoeveel impact heeft de rename? (DB, API, TypeScript, MCP, prompts)
- **Conclusie**: —

---

## GEPARKEERD (v3 of later)

| # | Onderwerp | Reden voor parkeren |
|---|---|---|
| V3-1 | Multi-sessie workflow engine | Eerst overhead meten, post-checks zijn 80% oplossing |
| V3-2 | Model-per-stap optimalisatie | Vereist multi-sessie |
| V3-3 | YAML workflow DSL (volledig) | Begin met checks.yaml, later uitbreiden |
| V3-4 | Human approval gates per story | Stuck-state recovery bestaat al |
| V3-5 | Tech debt sweep agent | Nice to have, niet kritisch voor v2 |

---

## Volgorde van besluiten

```
1. A1 (mega-sessie vs multi-sessie)   ← meet eerst de overhead
   └→ bepaalt A2, A3, en veel B-punten

2. A2 (workflow engine vs post-checks) ← vloeit voort uit A1

3. C1 = MVP scope                      ← wordt duidelijk na A1+A2

4. P1 (PO-Companion → DevEngine gap)   ← onafhankelijk, kan parallel
5. P2 (mq-testing resultaten terug)    ← onafhankelijk, kan parallel

6. I1-I7 (DevEngine intern)            ← details, na de grote keuzes

7. A4 (orchestrator refactoring)       ← bij implementatie start
```
