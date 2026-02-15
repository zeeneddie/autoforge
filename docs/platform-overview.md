# MarQed.ai Platform Overzicht

> Dit document beschrijft de volledige MarQed.ai platformarchitectuur: alle componenten, hun verantwoordelijkheden, en de datastromen ertussen.

## Componenten

Het MarQed.ai platform bestaat uit vijf componenten:

| Component | Rol | Doelgroep |
|-----------|-----|-----------|
| **Onboarding** | Codebase analyse, kennis opbouw, IFPUG functiepunten | Developer, Tech Lead |
| **Discovery Tool** | Requirements gathering: brownpaper (bestaand) en greenpaper (nieuwbouw) | Product Manager, Stakeholder |
| **PM Dashboard** | Hiërarchisch overzicht met drill-down, metriek, en intake portaal | Product Manager |
| **Plane** | Planning, backlog, sprint management (SSOT) | Product Manager, Developer |
| **MQ DevEngine** | Autonome code-uitvoering, testing, delivery | Developer |

## Platformdiagram

```
MarQed.ai Platform
+---------------------------------------------------------------------------+
|                                                                           |
|  ONBOARDING            DISCOVERY TOOL               PM DASHBOARD          |
|  (Codebase Analyse)    (Requirements)               (Monitoring)          |
|  +----------------+    +----------------------+     +------------------+  |
|  | Codebase scan  |    | Brownpaper:          |     | App > Epic >     |  |
|  | Gap analyse    |--->|  bevestig onboarding |     |  Feature > Story |  |
|  | Kennis opbouw  |    |  docu wat er is      |     |                  |  |
|  | IFPUG FP       |    |  + interview         |     | Per niveau:      |  |
|  |                |    |                      |     |  children, FP,   |  |
|  |                |    | Greenpaper:          |     |  tests, fase     |  |
|  |                |    |  nieuwbouw           |     |                  |  |
|  |                |    |  docu + interview    |     | CRUD: R / CR / F |  |
|  +-------+--------+    +----------+-----------+     +--+----+----+-----+  |
|          |                        |                    |    |    |        |
|          | IFPUG FP               | schrijft           |    |    |        |
|          | + kennis               | naar               |    |    |        |
|          |                        |                    |    |    |        |
|          |       +================+================+   |    |    |        |
|          |       ||        PLANE (SSOT)            ||--+    |    |        |
|          |       ||  Backlog, Cycles, Modules      || hierarchie |        |
|          |       ||  Prioritering, Voortgang       || + states   |        |
|          |       +================+====+===========+        |    |        |
|          |                  import |    ^ status            |    |        |
|          |                        v    | + feedback         |    |        |
|          |       +---------------------+---+                |    |        |
|          |       |       MQ DEVENGINE      |----------------+    |        |
|          |       |     Coding + Testing    |  test results       |        |
|          |       +-------------------------+                     |        |
|          |                                                       |        |
|          +-------------------------------------------------------+        |
|                         IFPUG FP                                          |
|                                                                           |
+---------------------------------------------------------------------------+
```

## Datastromen naar PM Dashboard

Het PM Dashboard aggregeert data uit drie bronnen:

```
+------------------+     +------------------+     +------------------+
|     Plane        |     |    MQ DevEngine     |     |   Onboarding     |
|                  |     |                  |     |                  |
| Modules (epics)  |     | TestRun records  |     | IFPUG functie-   |
| Work Items       |     | pass/fail counts |     |   punten per     |
| Sub-Work Items   |     | pass rate        |     |   entity         |
| States, Cycles   |     | agent_type       |     | Kennis-          |
| Progress %       |     | batch info       |     |   artefacten     |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        v
+------------------------------------------------------------------+
|                    Aggregatie API                                 |
|   Combineert hierarchie, test results, en functiepunten          |
+------------------------------------------------------------------+
         |
         v
+------------------------------------------------------------------+
|                    PM Dashboard                                   |
|   4-niveau drill-down met breadcrumb navigatie                   |
|   Metriek per niveau: children, FP, tests, fase                 |
|   Configureerbare CRUD-modus (R / CR / CRUD)                    |
+------------------------------------------------------------------+
```

| Bron | Data | Richting |
|------|------|----------|
| **Plane** | Modules (epics), Work Items (features), Sub-Work Items (stories), States, Cycles, voortgang % | Plane --> Dashboard |
| **MQ DevEngine** | TestRun records, pass/fail counts, pass rate, agent_type, batch info | MQ DevEngine --> Dashboard |
| **Onboarding** | IFPUG functiepunten per entity, codebase kennis-artefacten | Onboarding --> Dashboard |

## Discovery Tool: twee modi

De Discovery Tool heeft twee ingangen, afhankelijk van of er een bestaande codebase is:

### Brownpaper (bestaande codebase)

```
Onboarding output                PM / Stakeholder
(scan resultaten,         +      (domeinkennis,
 gap analyse,                     prioriteiten,
 IFPUG FP)                        feedback)
         \                       /
          v                     v
    +-----------------------------------+
    |  Discovery Tool - Brownpaper      |
    |                                   |
    |  1. Bevestig onboarding findings  |
    |  2. Documenteer wat er is         |
    |  3. Interview: wat moet anders?   |
    |  4. Decompositie tot micro items  |
    +-----------------------------------+
                    |
                    v
               Push naar Plane
```

**Brownpaper** is voor bestaande codebases. Onboarding heeft al gescand en bevindingen opgeleverd. De Discovery Tool presenteert deze bevindingen aan de PM ter bevestiging ("Klopt dit? Wat mist er?"), documenteert de huidige staat, en interviewt over gewenste wijzigingen en nieuwe functionaliteit.

### Greenpaper (nieuwbouw)

```
              PM / Stakeholder
              (visie, doelgroep,
               gewenste features)
                    |
                    v
    +-----------------------------------+
    |  Discovery Tool - Greenpaper      |
    |                                   |
    |  1. Documenteer visie & context   |
    |  2. Interview: wat wil je bouwen? |
    |  3. AI genereert hierarchie       |
    |  4. Decompositie tot micro items  |
    +-----------------------------------+
                    |
                    v
               Push naar Plane
```

**Greenpaper** is voor nieuwbouw. Er is geen bestaande codebase en dus geen Onboarding-output. De Discovery Tool start blanco met documentatie en interviews, en laat de AI een volledige hierarchie genereren.

## PM Dashboard: drill-down niveaus

```
Niveau 0: Applicatie
  |-- epics count, features count, stories count, totaal FP, totaal tests, overall voortgang
  |
  +-- Niveau 1: Epic (Plane Module)
       |-- features count, stories count, FP som, tests per categorie, voortgang
       |
       +-- Niveau 2: Feature (Plane Work Item)
            |-- stories count, FP som, tests per categorie, fase-status
            |
            +-- Niveau 3: User Story (Plane Sub-Work Item)
                 |-- FP, tests per categorie, AC status, fase-tracking
```

Navigatie via breadcrumbs: `Applicatie > Epic-naam > Feature-naam > Story-naam`

### Metriek per niveau

| Metriek | Niveau 0 (App) | Niveau 1 (Epic) | Niveau 2 (Feature) | Niveau 3 (Story) |
|---------|----------------|-----------------|--------------------|--------------------|
| Children count | epics, features, stories | features, stories | stories | -- |
| Functiepunten (FP) | totaal som | som features | som stories | individueel |
| Tests: unit | totaal | som features | som stories | individueel |
| Tests: integration | totaal | som features | som stories | individueel |
| Tests: e2e | totaal | som features | som stories | individueel |
| Fase-status | overall % | voortgang % | huidige fase | huidige fase |

### Fase-tracking model

Elk item doorloopt:

```
Discovery --> Planning --> Building --> Testing --> Review --> Done
                                                                |
                                  Blocked (dwars-status) -------+
```

Mapping naar Plane states:

| Plane state | Fase | Omschrijving |
|-------------|------|-------------|
| `backlog` | Discovery | Item is geidentificeerd, requirements worden verzameld |
| `unstarted` | Planning | Requirements zijn klaar, wacht op sprint toewijzing |
| `started` | Building / Testing | In uitvoering door MQ DevEngine |
| `completed` | Done | Afgerond en goedgekeurd |
| `cancelled` | Blocked | Geblokkeerd of geannuleerd |

### Configureerbare CRUD-modus

| Fase | Rechten | Doelgroep |
|------|---------|-----------|
| Fase 1 (standaard) | Read-only | Nieuwe klanten, monitoring |
| Fase 2 | Toevoegen + bekijken | Klanten die zelf items willen invoeren |
| Fase 3 | Volledige CRUD | Klanten met volledige autonomie |

## Intake: requirements, changes en bugs

Het PM Dashboard is niet alleen een monitoring-tool. Vanaf **CRUD fase 2** (toevoegen + bekijken) fungeert het als **intake-portaal** waar de PM nieuwe requirements, change requests en bug reports kan aanmaken -- direct op het juiste niveau in de hiërarchie.

### Businessmodel: FP-abonnementen

MarQed.ai biedt haar service aan op basis van **functiepunten-abonnementen**:

| Abonnement | FP/maand | Prijs |
|------------|----------|-------|
| Basis | 25 FP | €7.500/maand |
| *Overige staffels nader te bepalen* | | |

FP is niet alleen een sizing-metriek maar het **facturatiemodel**. Elke FP die de PM indient gaat van het maandbudget af. Dit maakt de inschatting commercieel bindend en de human-in-the-loop essentieel:

- PM moet weten wat een item "kost" in FP **voordat** het naar development gaat
- PM moet zien hoeveel FP-budget er nog resteert deze maand
- PM moet bewust kiezen: dit item indienen (en budget verbruiken) of niet
- Na decompositie (bij requirements) moet de PM de FP-breakdown per sub-item goedkeuren

Ongebruikte FP **vervallen** aan het eind van de maand -- geen rollover. Dit houdt het model simpel en voorspelbaar voor beide partijen. Bij maandwisseling reset de verbruikt/ingepland teller naar 0; items die al in de pipeline zitten tellen mee voor de maand waarin ze zijn ingediend.

### Drie intake-typen

| Type | Omschrijving | Voorbeeld | Route na intake |
|------|-------------|-----------|-----------------|
| **Nieuw requirement** | Uitbreiding van bestaande functionaliteit of geheel nieuwe feature | "We willen ook 2FA op de login" | PM Dashboard → Discovery Tool (brownpaper) → Plane → MQ DevEngine |
| **Change request** | Wijziging op een bestaand item; scope is duidelijk | "Zoekfunctie moet ook op categorie filteren" | PM Dashboard → Plane (direct) → MQ DevEngine |
| **Bug report** | Defect in bestaande functionaliteit | "Export knop crasht bij >1000 rijen" | PM Dashboard → Plane (direct, hoge prio) → MQ DevEngine |

### Intake flow

```
PM ziet in Dashboard:
  App > Betalen > Checkout Feature
        |
        +-- klikt [+] op Feature-niveau
        |
        v
  Intake formulier:
  +------------------------------------------+
  | Type:    (*) Requirement  ( ) Change  ( ) Bug  |
  | Titel:   [Export crasht bij >1000 rijen     ]  |
  | Omschrijving: [                             ]  |
  | Gekoppeld aan: Checkout Feature (auto)         |
  | Prioriteit: ( ) Critical (*) High ( ) Med ( ) Low |
  +------------------------------------------+
        |
        v
  AI FP-inschatting + PM review (human-in-the-loop #1):
  +-----------------------------------------------+
  |  Geschatte FP:  [  8 FP  ] <- aanpasbaar      |
  |                                                |
  |  Maandbudget:   ████████████░░░░  17/25 FP    |
  |  Na dit item:   ██████████████░░   9/25 FP    |
  |                                                |
  |  [ Indienen ]  [ Scope aanpassen ]  [ Annuleren ] |
  +-----------------------------------------------+
        |
        +------ Annuleren? -----> Geen item aangemaakt
        |
        v  (Indienen)
  Plane Work Item aangemaakt:
    - Label: "intake:bug" / "intake:change" / "intake:requirement"
    - Parent relatie: gekoppeld aan bestaand Plane item
    - Metadata: bron="pm-dashboard", intake_timestamp, pm_naam
    - FP: bevestigde inschatting
        |
        +------ Requirement? -----> Discovery Tool (brownpaper)
        |                           voor decompositie tot micro features
        |                                    |
        |                                    v
        |                           Human-in-the-loop #2:
        |                           PM review FP-breakdown
        |                             Feature A: 8 FP
        |                             Feature B: 10 FP
        |                             Feature C: 6 FP
        |                                    |
        |                                    v
        |                              Plane (gedecomponeerd)
        |                                    |
        +------ Change / Bug? ----------> Plane cycle (direct)
        |                                    |
        v                                    v
  MQ DevEngine pakt op, bouwt/fixt, test
        |
        v
  PM Dashboard toont resultaat:
    - Status per intake item
    - Welke acties ondernomen
    - Test results
    - FP verbruik
    - Link naar origineel intake item
```

### Routing: waarom drie routes?

| Type | Gaat via Discovery? | Reden |
|------|-------------------|-------|
| **Nieuw requirement** | Ja (brownpaper) | Moet gedecomponeerd worden tot micro features (max 2 uur). Kan impact hebben op meerdere epics/features. |
| **Change request** | Nee, direct naar Plane | Scope is afgebakend: wijziging op een bestaand, bekend item. Geen decompositie nodig. |
| **Bug report** | Nee, direct naar Plane | Fixes zijn klein en urgent. Snelle turnaround is belangrijker dan decompositie. |

Bij twijfel (is dit een change of een nieuw requirement?) kan de PM altijd kiezen voor "requirement" om via Discovery te gaan -- beter te veel decompositie dan te weinig.

### FP-inschatting bij intake

De FP-inschatting vindt plaats op **moment 3: post-intake, pre-routing**. De PM vult eerst het intake formulier in, krijgt dan een FP-inschatting te zien met budget-impact, en beslist pas daarna of het item doorgaat. Dit is de **human-in-the-loop**: de AI schat, de mens bevestigt.

#### Inschattingsbronnen

De AI-inschatting combineert drie bronnen:

| Bron | Beschikbaarheid | Wat het levert |
|------|----------------|----------------|
| **Beschrijving-analyse** | Altijd (tekst van PM) | AI analyseert complexiteit op basis van beschrijving, type, omvang |
| **Historische data** | Na eerste sprint | Gemiddelde FP van afgeronde items in dit project, per type en categorie |
| **Onboarding IFPUG** | Bij brownpaper (bestaande codebase) | IFPUG FP van het parent-item; mutaties op bestaande items zijn relatief inschatbaar |

Bij greenpaper (nieuwbouw) zonder historie is alleen bron 1 beschikbaar. De AI geeft dan een bredere range ("5-15 FP") en een lagere confidence score.

#### PM review: human-in-the-loop

| Intake type | Review #1 (intake) | Review #2 (na decompositie) |
|-------------|--------------------|-----------------------------|
| Requirement | Totaal FP inschatting + budget-impact | FP breakdown per sub-item na Discovery |
| Change | FP inschatting + budget-impact | -- (geen decompositie) |
| Bug | FP inschatting + budget-impact (meestal laag) | -- (geen decompositie) |

De PM kan bij review #1:

- **FP aanpassen**: de geschatte waarde handmatig bijstellen
- **Indienen**: item gaat door naar routing met de bevestigde FP
- **Scope aanpassen**: terug naar het formulier om de omschrijving te verfijnen
- **Annuleren**: geen item aangemaakt, geen FP verbruikt

Bij requirements komt na Discovery decompositie een **tweede review** waar de PM de FP-breakdown per sub-item ziet en goedkeurt voordat de items naar Plane gaan.

#### Admin-override

MarQed-admins kunnen elke FP-inschatting challengen en handmatig corrigeren -- zowel bij de initiële inschatting (review #1) als na decompositie (review #2). De gecorrigeerde waarde wordt als definitief gemarkeerd en de oorspronkelijke AI-schatting wordt bewaard voor kalibratie van het inschattingsmodel.

#### Budget dashboard

Het FP-budget is altijd zichtbaar in het PM Dashboard:

```
PM Dashboard - Budget
+-----------------------------------------------+
|  Maart 2026                     Basis (25 FP)  |
|  ████████████████░░░░░░░░░░      17/25 FP     |
|                                                 |
|  Verbruikt:    8 FP                             |
|  Resterend:   17 FP                             |
|  Ingepland:    5 FP                             |
|  Beschikbaar: 12 FP                             |
+-----------------------------------------------+
```

| Term | Betekenis |
|------|-----------|
| **Verbruikt** | FP van afgeronde items (status: Done) |
| **Resterend** | Totaal abonnement minus verbruikt |
| **Ingepland** | FP van items in huidige sprint (status: Building/Testing) |
| **Beschikbaar** | Resterend minus ingepland -- wat de PM nog kan indienen |

#### Overschrijdingsbeveiliging

| Situatie | Gedrag |
|----------|--------|
| Item past binnen beschikbaar budget | Normaal indienen |
| Item overschrijdt beschikbaar maar past binnen resterend | Waarschuwing: "Let op: hierna 0 FP beschikbaar deze maand" |
| Item overschrijdt maandbudget | Blokkeer + melding: "Dit item overschrijdt uw maandbudget. Neem contact op voor uitbreiding of wacht tot volgende maand." |
| Geen budget meer | Intake uitgeschakeld, alleen read-only dashboard |

### Intake overzicht in PM Dashboard

Naast de bestaande hiërarchie-view krijgt het Dashboard een **intake-overzicht**:

```
PM Dashboard
+---------------------------------------+--------------------------------------+
|  Hierarchie (drill-down)              |  Intake overzicht                    |
|                                       |                                      |
|  App > Betalen                        |  Filter: [Alle] [Open] [Actief] [Af]|
|    Epic: Checkout                     |                                      |
|      Feature: Betaalmethoden     [+]  |  BUG-001  Export crash     High      |
|      Feature: Order overzicht    [+]  |    FP: 3                            |
|      Feature: Data export        [+]  |    Status: Testing                   |
|        Story: CSV export              |    Gekoppeld: Data export            |
|        Story: PDF export              |    Aangemaakt: 01-03 door Jan        |
|        Story: Excel export            |    Tests: 3/3 passing                |
|                                       |                                      |
|    Epic: Facturatie                    |  CHG-003  Zoek filter    Medium      |
|      ...                              |    FP: 5                            |
|                                       |    Status: Building                  |
|                                       |    Gekoppeld: Zoekfunctie            |
|                                       |                                      |
|                                       |  REQ-007  2FA login      Low         |
|                                       |    FP: 13                           |
|                                       |    Status: Discovery                 |
|                                       |    Gekoppeld: Authenticatie          |
|                                       |    Route: brownpaper decompositie    |
+---------------------------------------+--------------------------------------+
```

De PM ziet in één oogopslag:
- **Wat** er is ingevoerd (titel, type, prioriteit)
- **Hoeveel FP** het item kost
- **Waar** het aan gekoppeld is (welk item in de hiërarchie)
- **Wat de status** is (Discovery / Planning / Building / Testing / Review / Done)
- **Welke acties** MQ DevEngine heeft ondernomen (builds, test results)
- **Wie** het heeft aangemaakt en wanneer

### Traceerbaarheid: audit trail

Elk intake item heeft een volledige audit trail, opgeslagen als Plane work item comments:

```
Audit trail voor BUG-001: "Export crasht bij >1000 rijen"
--------------------------------------------------------------------------------
[2026-03-01 14:23] INTAKE   PM Jan: Bug aangemaakt via PM Dashboard
                            Gekoppeld aan: Feature "Data Export" (FEAT-042)
                            Prioriteit: High
                            Omschrijving: "Bij klikken op Export met >1000 rijen
                            krijg je een timeout error. Verwacht: CSV download."

[2026-03-01 14:25] PLAN     Sync: Toegevoegd aan actieve Sprint Cycle 12
                            Reden: High priority bug, directe routing

[2026-03-01 15:30] BUILD    MQ DevEngine: Opgepakt door coding agent
                            Branch: fix/export-crash-1000-rows
                            Model: claude-sonnet-4-5

[2026-03-01 16:10] TEST     MQ DevEngine: Fix geimplementeerd + getest
                            Test results: 3/3 passing
                            - test_export_1000_rows: PASS
                            - test_export_5000_rows: PASS
                            - test_export_empty: PASS
                            Change doc: "Added cursor-based pagination to export
                            query, batch size 500 rows"

[2026-03-01 16:15] REVIEW   Status -> Review
                            PM Jan kan goedkeuren of afwijzen

[2026-03-01 17:00] DONE     PM Jan: Goedgekeurd
                            Comment: "Getest met 2000 rijen, werkt correct"
```

Elk audit trail event bevat:
- **Timestamp** (wanneer)
- **Fase** (INTAKE / PLAN / BUILD / TEST / REVIEW / DONE)
- **Actor** (wie: PM naam of "MQ DevEngine" of "Sync")
- **Actie** (wat er is gebeurd)
- **Details** (test results, branch naam, review comment)

### Plane labels en metadata

Elk intake item wordt in Plane aangemaakt met gestructureerde metadata:

| Veld | Waarde | Doel |
|------|--------|------|
| Label | `intake:bug` / `intake:change` / `intake:requirement` | Filteren en rapporteren per type |
| Label | `source:pm-dashboard` | Onderscheid van items uit Discovery Tool of directe Plane input |
| Parent | Bestaand Plane work item ID | Traceerbaarheid naar het item waar het bij hoort |
| Custom field | `intake_by` | PM naam voor audit trail |
| Custom field | `intake_at` | Timestamp van aanmaak |
| Description prefix | `[BUG]` / `[CHANGE]` / `[REQ]` | Visuele herkenning in Plane UI |

### Prioriteit-escalatie

| Intake type | Default prioriteit | Escalatie regel |
|-------------|-------------------|-----------------|
| Bug - Critical | Urgent | Gaat voor alles in huidige cycle, MQ DevEngine pakt direct op |
| Bug - High | High | Toegevoegd aan huidige cycle, volgende in queue |
| Bug - Medium/Low | Medium/Low | Toegevoegd aan backlog, PM plant in volgende cycle |
| Change request | Zoals ingevoerd | Geen escalatie, PM bepaalt prioriteit |
| Nieuw requirement | Low (default) | Na Discovery decompositie bepaalt PM de prioriteit per sub-item |

### Helpdesk-integratie (toekomstig)

> Dit is een architectuuridee voor latere sprints. Het intake-patroon (type → route → Plane → track) is identiek aan de PM Dashboard intake; alleen de bron verschilt.

```
Externe ITSM-platformen                    MarQed.ai Platform
+-------------------+                     +---------------------------+
| ServiceNow        |                     |                           |
| Zendesk           |---webhook/API--->   |  Intake API               |
| Jira SM           |                     |    - Ticket parsing       |
| Freshdesk         |                     |    - Type classificatie   |
| TOPdesk           |                     |      (bug/change/req)     |
+-------------------+                     |    - AI matching op       |
                                          |      bestaand item        |
                                          |    - Plane work item      |
                                          |      aanmaken             |
                                          +------------+--------------+
                                                       |
                                                       v
                                          PM Dashboard: toont extern
                                          ticket als intake item
                                            - Link naar bron-systeem
                                            - Bidirectioneel: status
                                              updates terug naar
                                              helpdesk
```

Connectors per platform zouden een **adapter-patroon** volgen:
- Gemeenschappelijke `IntakeEvent` interface
- Per platform een adapter die het ticket-formaat vertaalt
- AI-classificatie bepaalt type (bug/change/requirement) als het bron-systeem dat niet meelevert
- AI-matching koppelt het ticket aan het dichtstbijzijnde bestaande item in de hiërarchie

## Complete pipeline flow

### Initieel (nieuw project of onboarding)

```
1. Onboarding scant bestaande codebase (of: skip bij nieuwbouw)
                |
2. Discovery Tool: brownpaper (bevestig + interview) of greenpaper (blanco + interview)
                |
3. Twee-sporen review: PM business review + tech lead Git PR
                |
4. Push naar Plane (SSOT)
                |
5. MQ DevEngine importeert, bouwt, test, pusht status terug naar Plane
                |
6. PM monitort voortgang in PM Dashboard (data uit Plane + MQ DevEngine + Onboarding)
                |
7. Feedback loop: goedgekeurd = Done, afgekeurd = terug naar Discovery
```

### Doorlopend (intake op bestaande applicatie)

```
8. PM ziet item in Dashboard, klikt [+]
                |
9. Intake: kiest type (requirement / change / bug) + details
                |
10. AI FP-inschatting + budget-impact → PM bevestigt (human-in-the-loop)
                |
        +-------+-------+
        |               |
   Requirement     Change / Bug
        |               |
  Discovery Tool   Direct naar
  (brownpaper)     Plane cycle
        |               |
  FP-breakdown          |
  PM bevestigt          |
  (human-in-the-loop #2)|
        |               |
        v               v
11. MQ DevEngine bouwt/fixt, test, pusht resultaat
                |
12. PM ziet resultaat in Dashboard intake-overzicht
                |
13. PM reviewt: goedgekeurd = Done, afgekeurd = feedback
```

De twee flows (initieel en doorlopend) gebruiken dezelfde onderliggende infrastructuur: Plane als SSOT, MQ DevEngine als executie-engine, PM Dashboard als monitoring. Het verschil zit in de **ingang** (Discovery Tool vs. intake formulier) en de **routing** (altijd via Discovery vs. direct naar Plane).

---

## Strategische Architectuurkeuzes

### Multi-tenancy: schema-per-tenant

MarQed.ai bedient meerdere klanten, elk met meerdere applicaties. Data-isolatie is een harde eis: klanten mogen elkaars data niet zien.

**Aanpak: single platform, multi-tenant met schema-per-tenant in PostgreSQL.**

```
Tenant "Acme Corp"                    Tenant "Beta BV"
  schema: tenant_acme                   schema: tenant_beta
  ├── sessions                          ├── sessions
  ├── discovery_entities                ├── discovery_entities
  ├── acceptance_criteria               ├── acceptance_criteria
  ├── conversation_messages             ├── conversation_messages
  └── onboarding_context                └── onboarding_context
```

| Aspect | Multi-tenant (1 platform) | Per-klant (N platforms) |
|--------|--------------------------|------------------------|
| Data-isolatie | Schema-per-tenant | Volledige isolatie |
| Infra kosten | Laag (1 deployment) | Hoog (N deployments) |
| Updates uitrollen | 1x deployen | N keer deployen |
| Schaalbaarheid | Horizontaal schalen | Lineair duurder |
| Compliance | Complexer maar haalbaar | Eenvoudiger |

Voordelen schema-per-tenant:
- Volledige data-isolatie (geen per-ongeluk cross-tenant queries)
- Eenvoudig te backuppen/restoren per klant
- Een deployment, een codebase
- Kan later naar dedicated DB per klant als een enterprise klant dat eist

**Rechtenmodel per applicatie:**

```
Klant (tenant)
  └── Applicatie
       ├── Team (leden + rollen)
       └── Rechten per niveau:
            ├── Epic:    wie mag aanmaken / wijzigen / verwijderen
            ├── Feature: wie mag aanmaken / wijzigen / verwijderen
            └── Story:   wie mag aanmaken / wijzigen / verwijderen
```

Drie rollen per applicatie:
- **Viewer**: read-only (CRUD fase 1)
- **Editor**: intake + wijzigen (CRUD fase 2)
- **Admin**: volledige CRUD + team beheer (CRUD fase 3)

### Per-applicatie AI Team Profielen

Elke applicatie heeft een eigen tech stack en daarom een eigen team van AI-experts. Dit breidt het MQ DevEngine per-agent-type model concept uit naar een **team-profiel per applicatie**:

```
Applicatie "Webshop" (React + Python + PostgreSQL):
  Team profiel:
    - Coding agent:    claude-opus-4-6 (complex logic)
    - Testing agent:   claude-sonnet-4-5 (fast test generation)
    - Initializer:     claude-opus-4-6 (accurate decomposition)
    - Code reviewer:   claude-opus-4-6 (quality gate)
    - Prompt context:  "React 18, Python 3.12, PostgreSQL 15, REST API"

Applicatie "Mobile App" (React Native + Firebase):
  Team profiel:
    - Coding agent:    claude-opus-4-6
    - Testing agent:   claude-sonnet-4-5
    - Prompt context:  "React Native 0.73, Firebase, Expo"
```

Team-profielen zijn templates die je kunt hergebruiken en rouleren tussen applicaties. De prompt context wordt meegegeven aan alle agents zodat ze gespecialiseerd zijn in de juiste tech stack.

### War Room: real-time monitoring op 3-4 monitoren

Voor het kantoor/operatiecentrum: de hele pipeline live volgen op meerdere schermen.

```
Monitor 1: INTAKE          Monitor 2: PLANNING         Monitor 3: EXECUTIE        Monitor 4: KWALITEIT
+-------------------+    +-------------------+     +-------------------+     +-------------------+
| Nieuwe items      |    | Plane Backlog     |     | MQ DevEngine Status  |     | Test Results      |
| FP Budget meter   |    | Sprint Board      |     | Actieve agents    |     | Pass/Fail rates   |
| Wachtrij          |    | Prioriteiten      |     | Live code output  |     | Review queue      |
| Intake trend      |    | Sprint progress   |     | Build logs        |     | Kwaliteitsmetrics |
+-------------------+    +-------------------+     +-------------------+     +-------------------+
```

**Design principes:**
- **Dashboard-first design** met consistent design system (shadcn/ui)
- **Dark theme** voor monitors/TV's (betere leesbaarheid op afstand)
- **Card-based grid layout**, grote getallen, status-kleuren (groen/oranje/rood)
- **Grote typography** (leesbaar op 3m afstand), monospace voor code/logs
- **Real-time updates** via WebSocket of SSE zonder page refresh
- **Kiosk mode**: fullscreen, auto-rotate tussen views, geen navigatie nodig

### Supervisor Agent

Een meta-agent die boven de individuele agents staat en het hele proces bewaakt:

```
                    SUPERVISOR AGENT
                    (process orchestrator)
                           |
          +----------------+----------------+
          |                |                |
     Discovery Tool    Plane Sync      MQ DevEngine
     (quality check    (prioriteit     (agent health,
      op requirements)  optimalisatie)  stuck detection)
```

**Verantwoordelijkheden:**

1. **Monitort:** Ziet alle lopende processen, detecteert bottlenecks en failures
2. **Ingrijpt:** Als een coding agent vastloopt, stelt de supervisor een andere aanpak voor
3. **Optimaliseert:** Analyseert historische data en stelt procesverbeteringen voor
4. **Rapporteert:** Geeft management-niveau inzichten ("Sprint 8a loopt 20% achter op schema")
5. **Kwaliteit bewaakt:** Review van AI-output voordat het naar de klant gaat

**Fasering:**
- Fase 1 (minimaal): alerting bij failures + stuck detection
- Fase 2: proactieve suggesties, automatische herplanning
- Fase 3: kwaliteitsgate, automatische escalatie, management rapportage

### Dev/Prod Deployment: twee omgevingen

```
DEV (huidige machine)                    PROD (p920 / marqed003)
+-------------------------------+       +-------------------------------+
| MQ DevEngine (source, ./venv/)   |       | MQ DevEngine (npm global)        |
| Plane (Docker, localhost:8080)|       | Plane (Docker, :8080)         |
| MarQed Discovery (source)     |       | MarQed Discovery (gebouwd)    |
| Claude Code (dev tools)       |       | Claude CLI (agents)           |
| SQLite (~/.mq-devengine/)        |       | SQLite (~/.mq-devengine/)        |
+-------------------------------+       +-------------------------------+
         ontwikkelen                          valideren + draaien
```

**Deployment stappen p920:**

1. `npm install -g mq-devengine-ai` (CLI + backend + UI)
2. `mq-devengine config` (stel .env in: Claude API key, Plane URL)
3. Plane Docker Compose opzetten op p920
4. MarQed import tree importeren in Plane
5. MQ DevEngine agents starten op mq-discovery project
6. Validatie: volledige pipeline draait vanaf scratch

**Vereisten:**
- `AUTOFORGE_ALLOW_REMOTE=1` in .env op p920
- Firewall: poort 8888 (MQ DevEngine) + 8080 (Plane) open binnen intern netwerk
- SSH toegang voor deployment en monitoring
- Git repo voor mq-discovery project

De p920 deployment valideert dat het platform reproduceerbaar is: als alles op een verse machine draait, is het platform klaar voor klant-deployments.
