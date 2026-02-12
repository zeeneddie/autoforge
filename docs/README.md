# AutoForge Documentatie

## Architectuur & Ontwerp

- [**architecture.md**](architecture.md) - Systeemarchitectuur: MarQed + Plane + AutoForge pipeline, component overzicht, test history, analytics dashboard, webhooks, deployment
- [**platform-overview.md**](platform-overview.md) - MarQed.ai platform: 5 componenten, platformdiagram, datastromen, brownpaper/greenpaper, PM Dashboard
- [**roadmap.md**](roadmap.md) - Sprint planning v2 (7 sprints voltooid, Sprint 7.1/7.2 gepland: per-project sync fix, graceful shutdown)

## Operations & Setup

- [**operations-guide.md**](operations-guide.md) - Plane + AutoForge opstarten, sync configureren, agent starten, troubleshooting
- [**github-setup.md**](github-setup.md) - GitHub Organization setup, repository structuur, fork management

## Architectuur Decision Records (ADR)

- [**ADR-001: Plane Integratie**](decisions/ADR-001-plane-integration.md) - Waarom Plane als PM frontend ipv zelf bouwen. Alternatieven, risico's, roadmap impact.
- [**ADR-002: Analyse Pipeline**](decisions/ADR-002-analysis-pipeline.md) - Waar analyse, review, executie plaatsvindt. MarQed -> Git PR -> Plane -> AutoForge. Change document formaat.
- [**ADR-003: Data Mapping**](decisions/ADR-003-data-mapping.md) - Entity/state/priority mapping tussen MarQed, Plane en AutoForge. Echo prevention. DB schema uitbreiding.
- [**ADR-004: Per-Project Plane Sync**](decisions/ADR-004-per-project-plane-sync.md) - Per-project Plane sync configuratie. Voorkomt cross-project data lekkage bij meerdere projecten.

## Plane Sync Module

- [**api-design.md**](plane-sync/api-design.md) - REST API endpoints: config, cycles, import, sync, webhooks, test-report, test-history, release-notes, sprint completion
- [**sprint-lifecycle.md**](plane-sync/sprint-lifecycle.md) - Complete sprint lifecycle: 7 fasen, test history, webhooks, release notes, foutscenario's
