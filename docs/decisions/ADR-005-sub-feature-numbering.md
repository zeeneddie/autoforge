# ADR-005: Sub-feature Nummering bij "Story X.XX" Import

**Status:** Geaccepteerd — geïmplementeerd 2026-03-26
**Beslisser:** Eddie

## Context

Wanneer een feature vanuit mq-planning (Plane) geïmporteerd wordt, krijgt de naam het format:

```
Story 1.01 — RequirementsAgent — mq_req_analyst
```

Bij het aanmaken van sub-features via `feature_create_sub_features` extracteerde de bestaande code het numerieke prefix via:

```python
_pfx = re.match(r'^(\d+(?:\.\d+)*)', parent.name)
parent_prefix = _pfx.group(1) if _pfx else str(feature_id)
```

Omdat de naam begint met `"Story "` (niet-numeriek), gaf de regex geen match. Het systeem viel terug op `str(feature_id)` (bijv. `"1"`), waardoor sub-features de nummering `"1.1"`, `"1.2"`, `"1.3"` kregen in plaats van `"1.01.1"`, `"1.01.2"`, `"1.01.3"`.

**Impact:** Sub-features van Story 1.01 zagen eruit als `"1.1"` — verwarring met andere story-nummers (bijv. Story 1.10 → `"1.10"`), en conflicterend met de hiërarchische naamgeving.

## Besluit

Regex uitgebreid om ook `"Story X.XX — ..."` format te herkennen:

```python
# Oud:
_pfx = re.match(r'^(\d+(?:\.\d+)*)', parent.name)

# Nieuw:
_pfx = re.match(r'^(?:Story\s+)?(\d+(?:\.\d+)*)', parent.name)
```

De `(?:Story\s+)?` optionele prefix zorgt dat:
- `"Story 1.01 — Foo"` → extraheert `"1.01"` → sub-features: `"1.01.1"`, `"1.01.2"`
- `"1.1 Foo"` → extraheert `"1.1"` → sub-features: `"1.1.1"`, `"1.1.2"` (bestaand gedrag)
- `"3 Foo"` → extraheert `"3"` → sub-features: `"3.1"`, `"3.2"` (bestaand gedrag)

## Verwachte hiërarchie

```
Story 1.01 — RequirementsAgent    (geïmporteerd uit mq-planning)
├── 1.01.1  BMAD agent-files aanmaken
├── 1.01.2  AgentLoader implementeren
├── 1.01.3  BaseAgent abstracte klasse
├── 1.01.4  mq_req_analyst agent implementatie
└── 1.01.5  Unit tests voor analyst agent
```

## Gewijzigd bestand

`mcp_server/feature_mcp.py` — regel ~1734

## Migratie bestaande data

De 5 verkeerd genummerde sub-features in project `mq-po-companion` zijn direct hernoemd:
- `1.1 BMAD agent-files...` → `1.01.1 BMAD agent-files...`
- `1.2 AgentLoader...` → `1.01.2 AgentLoader...`
- `1.3 BaseAgent...` → `1.01.3 BaseAgent...`
- `1.4 mq_req_analyst...` → `1.01.4 mq_req_analyst...`
- `1.5 Unit tests...` → `1.01.5 Unit tests...`
