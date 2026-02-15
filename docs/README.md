# MQ DevEngine Documentatie

## Architectuur & Ontwerp

- [**architecture.md**](architecture.md) - Systeemarchitectuur: MarQed + MQ Planning + MQ DevEngine pipeline, component overzicht, test history, analytics dashboard, webhooks, deployment
- [**platform-overview.md**](platform-overview.md) - MarQed.ai platform: 5 componenten, platformdiagram, datastromen, brownpaper/greenpaper, PM Dashboard
- [**roadmap.md**](roadmap.md) - Sprint planning v2 (7 sprints + 7.1 voltooid, Sprint 7.2 gepland: graceful shutdown)

## Operations & Setup

- [**operations-guide.md**](operations-guide.md) - MQ Planning + MQ DevEngine opstarten, sync configureren, agent starten, troubleshooting
- [**github-setup.md**](github-setup.md) - GitHub Organization setup, repository structuur, fork management

## Architectuur Decision Records (ADR)

- [**ADR-001: MQ Planning Integratie**](decisions/ADR-001-plane-integration.md) - Waarom MQ Planning (Plane) als PM frontend ipv zelf bouwen. Alternatieven, risico's, roadmap impact.
- [**ADR-002: Analyse Pipeline**](decisions/ADR-002-analysis-pipeline.md) - Waar analyse, review, executie plaatsvindt. MarQed -> Git PR -> MQ Planning -> MQ DevEngine. Change document formaat.
- [**ADR-003: Data Mapping**](decisions/ADR-003-data-mapping.md) - Entity/state/priority mapping tussen MarQed, MQ Planning en MQ DevEngine. Echo prevention. DB schema uitbreiding.
- [**ADR-004: Per-Project Planning Sync**](decisions/ADR-004-per-project-plane-sync.md) - Per-project MQ Planning sync configuratie. Voorkomt cross-project data lekkage bij meerdere projecten.

## Planning Sync Module

- [**api-design.md**](planning-sync/api-design.md) - REST API endpoints: config, cycles, import, sync, webhooks, test-report, test-history, release-notes, sprint completion
- [**sprint-lifecycle.md**](planning-sync/sprint-lifecycle.md) - Complete sprint lifecycle: 7 fasen, test history, webhooks, release notes, foutscenario's
