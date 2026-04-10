# DevEngine v2 — Sprint Plan

> Integreert met de mq-platform Master Roadmap (ROADMAP.md).
> v2 werk past in **Fase 2-3** van de platform roadmap.
> Walking skeleton (Sprint 0) kan parallel met Fase 1 tail-end.

---

## Positie in de platform roadmap

```
Platform Fase 1 (mrt-apr)     Platform Fase 2 (apr-mei)     Platform Fase 3 (mei-jun)
─────────────────────────     ─────────────────────────     ─────────────────────────
1A: mq-testing op P920  ✓    2A: Feedback loop             3A: Dogfooding
1B: Pipeline sluiten         2C: Orchestratie              3B: Agents leren
1C: DevEngine stabiliseren ✓ 2E: Adversarial evaluator     3C: Klantmigraties
1D: Supervisor bootstrap
1E: PO-Companion Sprint 1
                              
                              ┌─── DevEngine v2 START ───┐
                              │                           │
                              │ Sprint 0: Post-checks     │ ← Fase 2 week 1
                              │ Sprint 1: Kern rename     │ ← Fase 2 week 2-3
                              │ Sprint 2: Wiki + contracts│ ← Fase 2 week 4
                              │ Sprint 3: mq-testing integ│ ← Fase 3 week 1-2
                              │ Sprint 4: PO feedback     │ ← Fase 3 week 3
                              │ Sprint 5: Help-content    │ ← Fase 3 week 4
                              │                           │
                              └───────────────────────────┘
```

### Aansluiting op bestaande taken

| Platform taak | DevEngine v2 equivalent | Vervangt of vult aan? |
|---|---|---|
| 2A.3 AC traceability | Sprint 1: steps → acceptance_criteria + git commit per story | VERVANGT |
| 2A.5 Build history | Sprint 1: kosten tracking + retry teller | VULT AAN |
| 2E Adversarial evaluator | Sprint 1: Codex vervangt review agent | VERVANGT 2E.2-2E.5 |
| 3B.8 Eval Set B | Sprint 0: deterministic post-checks | VULT AAN (post-checks zijn de eval) |
| 3B.11 Complexiteitsbudget | Sprint 1: story sizing model | VULT AAN |
| Golf 1: devEngine validatielus | Sprint 0: post-checks (lint, mock, test, coverage) | IS DIT |

---

## Sprint 0: Walking Skeleton — Post-checks

> **Doel**: Agent kan niet meer zelf bepalen dat het "klaar" is.
> **Duur**: 1 sprint (6 dagen)
> **Dependencies**: Geen. Kan morgen starten.
> **Platform fase**: Fase 2, week 1. Sluit aan bij Golf 1 (validatielus).

| # | Taak | Moeite | Repo |
|---|---|---|---|
| 0.1 | `post_checks.py` module aanmaken naast orchestrator | Klein | mq-devEngine |
| 0.2 | Lint + type-check als deterministic post-step | Klein | mq-devEngine |
| 0.3 | Mock data grep als deterministic post-step | Klein | mq-devEngine |
| 0.4 | Alle tests draaien als deterministic post-step | Klein | mq-devEngine |
| 0.5 | Test coverage meting (>= 80% gewijzigde files) | Middel | mq-devEngine |
| 0.6 | Bij falen: retry coding agent met foutmelding als context | Middel | mq-devEngine |
| 0.7 | `checks.yaml` laden: default checks + project-specifieke | Klein | mq-devEngine |
| 0.8 | YOLO mode verwijderen | Klein | mq-devEngine |
| 0.9 | WebSocket: `post_check_update` message type voor UI | Klein | mq-devEngine |
| 0.10 | UI: mini-stepper op AgentCard (checks voortgang) | Middel | mq-devEngine/ui |

**Deliverable**: Elke story doorloopt verplichte checks. Mock data probleem opgelost. 80% kwaliteitsverbetering.

**Aansluiting platform roadmap**:
- Realiseert Golf 1 "devEngine validatielus" (generate → test → iterate max 3x)
- Vervangt 3B.8 "Eval Set B" (post-checks ZIJN de eval)

---

## Sprint 1: DevEngine Kern

> **Doel**: Terminologie, traceerbaarheid, onafhankelijke review.
> **Duur**: 2 sprints (12 dagen)
> **Dependencies**: Sprint 0 klaar.
> **Platform fase**: Fase 2, week 2-3.

| # | Taak | Moeite | Repo |
|---|---|---|---|
| 1.1 | DB: Feature tabel rename naar Story | Middel | mq-devEngine |
| 1.2 | DB: `steps` kolom rename naar `acceptance_criteria` | Klein | mq-devEngine |
| 1.3 | DB: `tasks` JSON kolom verwijderen (sub-features zijn aparte records) | Klein | mq-devEngine |
| 1.4 | DB migratiescript v1 → v2 | Middel | mq-devEngine |
| 1.5 | API endpoints: /features → /stories | Middel | mq-devEngine |
| 1.6 | TypeScript types: Feature → Story | Middel | mq-devEngine/ui |
| 1.7 | MCP tools: feature_* → story_* (of backward-compat aliases) | Middel | mq-devEngine |
| 1.8 | Prompt templates: "feature" → "user story" | Klein | mq-devEngine |
| 1.9 | Codex review integratie (vervangt review agent) | Groot | mq-devEngine |
| 1.10 | Codex review: AC's + tech stack + DoD checklist als input | Middel | mq-devEngine |
| 1.11 | Codex reject → retry flow (max 3x, dan escalatie) | Middel | mq-devEngine |
| 1.12 | Git commit per story door orchestrator (deterministic) | Middel | mq-devEngine |
| 1.13 | Story planner: sizing hints (context radius, wijziging scope) | Middel | mq-devEngine |
| 1.14 | Review agent feature flag verwijderen (standaard aan via Codex) | Klein | mq-devEngine |
| 1.15 | UI: Goals view — AC's + taken + drill-down tool-calls | Groot | mq-devEngine/ui |
| 1.16 | UI: Verificatie-volgorde (AC's → Codex → tests → lint → mock → regressie → PO) | Middel | mq-devEngine/ui |

**Deliverable**: Consistente terminologie, traceerbaarheid (story → commit), onafhankelijke Codex review, Goals view in UI.

**Aansluiting platform roadmap**:
- Vervangt 2E.2-2E.5 (adversarial evaluator → Codex)
- Realiseert 2A.3 (AC traceability)
- Vult 2A.5 aan (build history: retry teller + kosten per story)
- Realiseert 3B.11 deels (complexiteitsbudget via sizing hints)

---

## Sprint 2: Wiki + API Contracts

> **Doel**: Project-context beschikbaar voor DevEngine via mq-wiki.
> **Duur**: 1 sprint (6 dagen)
> **Dependencies**: Sprint 1 klaar. mq-wiki basis moet beschikbaar zijn.
> **Platform fase**: Fase 2, week 4.

| # | Taak | Moeite | Repo |
|---|---|---|---|
| 2.1 | mq-wiki: project-domein structuur (wiki-project-{naam}) | Middel | mq-wiki |
| 2.2 | mq-wiki: API endpoint voor sources lezen (arch.md, prd.md) | Klein | mq-wiki |
| 2.3 | PO-Companion: push arch.md + prd.md naar wiki bij export | Middel | mq-PO-Companion |
| 2.4 | DevEngine: lees arch.md van wiki API bij sprint start | Middel | mq-devEngine |
| 2.5 | DevEngine: inject tech stack context in coding agent prompt | Klein | mq-devEngine |
| 2.6 | API contract: DevEngine → mq-testing trigger format | Klein | mq-platform |
| 2.7 | API contract: mq-testing → DevEngine resultaten format | Klein | mq-platform |
| 2.8 | API contract: mq-testing → PO-Companion resultaten format | Klein | mq-platform |

**Deliverable**: DevEngine weet welke tech stack het project gebruikt. API contracts liggen vast.

**Aansluiting platform roadmap**:
- Realiseert de gap PO-Companion → DevEngine (P1)
- Bereidt Sprint 3 voor (mq-testing integratie)
- Sluit aan bij Golf 0 "contract op elke actieve grens" (1D.4)

---

## Sprint 3: mq-testing Integratie

> **Doel**: Volledige verificatie-piramide werkt.
> **Duur**: 2 sprints (12 dagen)
> **Dependencies**: Sprint 2 klaar. mq-testing moet operationeel zijn (1A).
> **Platform fase**: Fase 3, week 1-2.

| # | Taak | Moeite | Repo |
|---|---|---|---|
| 3.1 | DevEngine: trigger mq-testing bij story done (module tests) | Middel | mq-devEngine |
| 3.2 | DevEngine: trigger mq-testing bij feature done (integratie + e2e + UI) | Middel | mq-devEngine |
| 3.3 | DevEngine: trigger mq-testing bij sprint done (full suite) | Klein | mq-devEngine |
| 3.4 | DevEngine: ontvang test resultaten van mq-testing (webhook) | Middel | mq-devEngine |
| 3.5 | DevEngine: test resultaten opslaan per story/AC in DB | Middel | mq-devEngine |
| 3.6 | DevEngine: bij app_bug → automatic retry coding agent | Middel | mq-devEngine |
| 3.7 | mq-testing: trigger endpoint uitbreiden voor DevEngine format | Middel | mq-testing |
| 3.8 | mq-testing: resultaten webhook naar DevEngine + mq-planning | Middel | mq-testing |
| 3.9 | mq-testing: resultaten naar PO-Companion | Middel | mq-testing |
| 3.10 | mq-testing: load test op feature niveau | Middel | mq-testing |
| 3.11 | UI: test resultaten per story (verificatie-volgorde) | Middel | mq-devEngine/ui |
| 3.12 | UI: feature acceptance test status | Klein | mq-devEngine/ui |
| 3.13 | mq-planning: status update bij feature test pass/fail | Klein | mq-devEngine |

**Deliverable**: Story done → module tests → feature done → integratie test → resultaten terug. Volledige keten werkt.

**Aansluiting platform roadmap**:
- Realiseert 2A.4 (E2E pipeline test)
- Bouwt voort op 1A (mq-testing operationeel)
- Sluit feedback loop deels (2A.1-2A.2)

---

## Sprint 4: PO Feedback Loop

> **Doel**: PO ziet alles in PO-Companion.
> **Duur**: 1 sprint (6 dagen)
> **Dependencies**: Sprint 3 klaar.
> **Platform fase**: Fase 3, week 3.

| # | Taak | Moeite | Repo |
|---|---|---|---|
| 4.1 | PO-Companion: portfolio view (leest mq-planning + DevEngine + mq-testing) | Groot | mq-PO-Companion |
| 4.2 | PO-Companion: story status per feature (in definitie / gepland / in bouw / getest / geaccepteerd) | Middel | mq-PO-Companion |
| 4.3 | PO-Companion: notificatie bij feature test failure | Klein | mq-PO-Companion |
| 4.4 | PO-Companion: human-in-the-loop flow (Codex reject escalatie + test failure escalatie) | Middel | mq-PO-Companion |
| 4.5 | PO-Companion: kosten dashboard (tokens, kosten per story/feature/sprint) | Middel | mq-PO-Companion |
| 4.6 | DevEngine: API endpoint voor kosten + voortgang per story | Klein | mq-devEngine |

**Deliverable**: PO ziet in PO-Companion de complete status van alles downstream. Human-in-the-loop bij escalatie.

**Aansluiting platform roadmap**:
- Realiseert PO-Companion portfolio view (P3)
- Bouwt voort op 2C (orchestratie / live status)

---

## Sprint 5: Help-content + Support

> **Doel**: Wiki genereert help-content automatisch.
> **Duur**: 1 sprint (6 dagen)
> **Dependencies**: Sprint 3 klaar (test resultaten + screenshots beschikbaar).
> **Platform fase**: Fase 3, week 4.

| # | Taak | Moeite | Repo |
|---|---|---|---|
| 5.1 | mq-wiki: auto-genereer feature entity page bij feature done | Middel | mq-wiki |
| 5.2 | mq-wiki: auto-genereer help pages uit AC's + error scenarios | Middel | mq-wiki |
| 5.3 | mq-wiki: embed mq-testing screenshots in help pages | Klein | mq-wiki |
| 5.4 | mq-wiki: knowledge graph updates (feature → story → help → bug) | Middel | mq-wiki |
| 5.5 | mq-wiki: sprint report generatie | Klein | mq-wiki |
| 5.6 | mq-wiki: "Bekend probleem" toevoegen bij mq-planning bug aanmaak | Klein | mq-wiki |
| 5.7 | mq-wiki: FAQ zoek-interface (/help route) | Middel | mq-wiki |

**Deliverable**: Help-content automatisch gegenereerd. Supportdesk kan wiki raadplegen. Fase 1+2 van support overlay.

**Aansluiting platform roadmap**:
- Nieuw — past in Fase 3 (platform bouwt zichzelf)
- Bouwt voort op mq-wiki roadmap ("platform project-wiki als mq-brain module")

---

## Totaaloverzicht

```
Sprint  Duur     Wat                           Repos              Platform fase
──────  ─────    ───────────────────────────    ─────────────────  ─────────────
  0     6 dagen  Post-checks (walking skeleton) mq-devEngine       Fase 2 / Golf 1
  1     12 dagen Kern (rename, Codex, goals UI) mq-devEngine       Fase 2
  2     6 dagen  Wiki + API contracts           mq-wiki, mq-DE,    Fase 2
                                                mq-POC, mq-plat
  3     12 dagen mq-testing integratie          mq-devEngine,      Fase 3
                                                mq-testing
  4     6 dagen  PO feedback loop               mq-PO-Companion,   Fase 3
                                                mq-devEngine
  5     6 dagen  Help-content + support         mq-wiki            Fase 3
──────  ─────    ───────────────────────────
TOTAAL  48 dagen (~8 sprints van 6 dagen)

Repos geraakt: 5 (mq-devEngine, mq-testing, mq-wiki, mq-PO-Companion, mq-platform)
```

### Waarde per sprint

```
Na sprint 0:  DevEngine levert betrouwbare code (80% verbetering)
Na sprint 1:  Code is traceerbaar + onafhankelijk gereviewd + goals zichtbaar
Na sprint 2:  DevEngine kent de tech stack, API contracts liggen vast
Na sprint 3:  Volledige verificatie-piramide werkt (8 vinkjes per story)
Na sprint 4:  PO ziet alles, human-in-the-loop werkt
Na sprint 5:  Help-content automatisch, supportdesk heeft een kennisbron
```

### Risico's

| Risico | Impact | Mitigatie |
|---|---|---|
| Codex integratie complexer dan verwacht | Sprint 1 loopt uit | Codex eerst als los script testen, dan integreren |
| mq-testing niet klaar (1A) als Sprint 3 start | Sprint 3 geblokkeerd | Sprint 3 kan niet eerder dan Fase 3; 1A moet af in Fase 1 |
| mq-wiki project-domein is meer werk dan verwacht | Sprint 2 loopt uit | Minimale scope: alleen API endpoint voor arch.md lezen |
| PO-Companion heeft geen capacity voor portfolio view | Sprint 4 geblokkeerd | Portfolio view als standalone pagina, niet geintegreerd |
| Token-kosten tracking (I2) is niet opgelost | Sprint 4.5 mist data | Schatting als fallback, later exact als SDK het ondersteunt |

---

## Relatie tot andere roadmap-taken

| Platform taak | Status na v2 | Opmerking |
|---|---|---|
| 2A.3 AC traceability | GEREALISEERD | Door Sprint 1 (rename + git commit per story) |
| 2A.5 Build history | GEREALISEERD | Door Sprint 1 (retry teller + kosten) |
| 2E Adversarial evaluator | GEREALISEERD | Door Sprint 1 (Codex vervangt review agent) |
| 3B.8 Eval Set B | GEREALISEERD | Door Sprint 0 (post-checks = eval) |
| 3B.11 Complexiteitsbudget | DEELS | Door Sprint 1 (sizing hints) |
| Golf 1 validatielus | GEREALISEERD | Door Sprint 0 (generate → check → iterate) |
| 2A.1-2A.2 Feedback loop | DEELS | Door Sprint 3 (mq-testing resultaten terug) |
| 2A.4 E2E pipeline test | GEREALISEERD | Door Sprint 3 (DevEngine → mq-testing → resultaten) |
