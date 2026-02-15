# ADR-004: Per-Project MQ Planning Sync Configuratie

**Status:** Voorgesteld
**Datum:** 2026-02-12
**Beslisser:** Eddie

## Context

MQ DevEngine ondersteunt meerdere projecten tegelijk (bijv. `klaverjas_app` en `mq-discovery`). De MQ Planning sync configuratie (cycle_id, project_id, workspace, sync_enabled) wordt momenteel **globaal** opgeslagen in de registry (`~/.mq-devengine/registry.db` via `set_setting()`/`get_setting()`).

Dit veroorzaakt een kritiek probleem: de background sync loop importeert work items uit één Plane cycle naar **alle** projecten. In de praktijk lekte de klaverjas "Sprint A: Auth + Teams" cycle (34 features) herhaaldelijk in de `mq-discovery` features database.

### Huidige architectuur (gebroken)

```
registry.db (globaal)
  planning_cycle_id = "f5252a9e-..."     ← 1 cycle voor alles
  planning_sync_enabled = "true"
  planning_project_id = "..."

background.py: PlanningSyncLoop
  → import_cycle() → schrijft naar ALLE project features.db's
```

### Impact

- Features uit project A verschijnen in project B
- Verwijderen helpt niet — de sync voegt ze bij de volgende poll weer toe
- Workaround: sync handmatig uitzetten (`planning_sync_enabled=false`)

## Besluit

MQ Planning sync configuratie wordt **per MQ DevEngine-project** opgeslagen.

### Nieuwe architectuur

```
registry.db
  planning_cycle_id:klaverjas_app = "f5252a9e-..."
  planning_sync_enabled:klaverjas_app = "true"
  planning_project_id:klaverjas_app = "abc123"

  planning_cycle_id:mq-discovery = "..."
  planning_sync_enabled:mq-discovery = "false"
  planning_project_id:mq-discovery = "def456"

background.py: PlanningSyncLoop
  → voor elk geregistreerd project:
       als sync_enabled: import_cycle(project_dir, cycle_id)
```

### Implementatieplan

1. **Registry keys uitbreiden:** `planning_*` settings krijgen een `:project_name` suffix
   - `get_setting("planning_cycle_id")` → `get_setting("planning_cycle_id:klaverjas_app")`
   - Backward-compat: als key zonder suffix bestaat, gebruik die als fallback

2. **Sync loop per-project:** `PlanningSyncLoop._poll()` itereert over `list_registered_projects()`, leest per-project config, en sync't alleen projecten met `planning_sync_enabled:X = true`

3. **API endpoints:** `GET/POST /api/planning/config` krijgen optionele `?project_name=X` parameter
   - Zonder param: legacy gedrag (globale config)
   - Met param: project-specifieke config

4. **UI:** SettingsModal MQ Planning sectie toont config per geselecteerd project

5. **Migratie:** bij eerste start na update, kopieer globale `planning_*` settings naar het eerste geregistreerde project

### Alternatieven overwogen

| Alternatief | Reden afgewezen |
|---|---|
| MQ Planning config in `features.db` per project | Mixen van concerns: features.db is voor feature data, niet configuratie |
| Aparte config file per project (`.mq-devengine/planning.json`) | Inconsistent met bestaand registry pattern |
| Project-specifieke DB tabel in registry.db | Overkill — registry key suffix is eenvoudiger |

## Gevolgen

- Meerdere projecten kunnen tegelijk met MQ Planning sync draaien
- Elk project koppelt aan zijn eigen MQ Planning workspace/project/cycle
- Geen cross-project data lekkage meer
- Bestaande single-project setups blijven werken (migratie)
