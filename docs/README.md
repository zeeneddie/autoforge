# AutoForge Documentatie

## Architectuur & Ontwerp

- [**architecture.md**](architecture.md) - Systeemarchitectuur: MarQed + Plane + AutoForge pipeline, component overzicht, deployment
- [**roadmap.md**](roadmap.md) - Sprint planning v2 (5 sprints, Plane-integratie)

## Architectuur Decision Records (ADR)

- [**ADR-001: Plane Integratie**](decisions/ADR-001-plane-integration.md) - Waarom Plane als PM frontend ipv zelf bouwen. Alternatieven, risico's, roadmap impact.
- [**ADR-002: Analyse Pipeline**](decisions/ADR-002-analysis-pipeline.md) - Waar analyse, review, executie plaatsvindt. MarQed -> Git PR -> Plane -> AutoForge. Change document formaat.
- [**ADR-003: Data Mapping**](decisions/ADR-003-data-mapping.md) - Entity/state/priority mapping tussen MarQed, Plane en AutoForge. Echo prevention. DB schema uitbreiding.

## Plane Sync Module

- [**api-design.md**](plane-sync/api-design.md) - REST API endpoints voor Plane integratie: config, test-connection, cycles, import, sync, webhooks
- [**sprint-lifecycle.md**](plane-sync/sprint-lifecycle.md) - Complete sprint lifecycle van analyse tot completion, alle 7 fasen, foutscenario's
