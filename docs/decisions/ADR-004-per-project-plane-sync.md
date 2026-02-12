# ADR-004: Per-Project Plane Sync Configuratie

**Status:** Voorgesteld
**Datum:** 2026-02-12
**Beslisser:** Eddie

## Context

AutoForge ondersteunt meerdere projecten tegelijk (bijv. `klaverjas_app` en `marqed-discovery`). De Plane sync configuratie (cycle_id, project_id, workspace, sync_enabled) wordt momenteel **globaal** opgeslagen in de registry (`~/.autoforge/registry.db` via `set_setting()`/`get_setting()`).

Dit veroorzaakt een kritiek probleem: de background sync loop importeert work items uit één Plane cycle naar **alle** projecten. In de praktijk lekte de klaverjas "Sprint A: Auth + Teams" cycle (34 features) herhaaldelijk in de `marqed-discovery` features database.

### Huidige architectuur (gebroken)

```
registry.db (globaal)
  plane_cycle_id = "f5252a9e-..."     ← 1 cycle voor alles
  plane_sync_enabled = "true"
  plane_project_id = "..."

background.py: PlaneSyncLoop
  → import_cycle() → schrijft naar ALLE project features.db's
```

### Impact

- Features uit project A verschijnen in project B
- Verwijderen helpt niet — de sync voegt ze bij de volgende poll weer toe
- Workaround: sync handmatig uitzetten (`plane_sync_enabled=false`)

## Besluit

Plane sync configuratie wordt **per AutoForge-project** opgeslagen.

### Nieuwe architectuur

```
registry.db
  plane_cycle_id:klaverjas_app = "f5252a9e-..."
  plane_sync_enabled:klaverjas_app = "true"
  plane_project_id:klaverjas_app = "abc123"

  plane_cycle_id:marqed-discovery = "..."
  plane_sync_enabled:marqed-discovery = "false"
  plane_project_id:marqed-discovery = "def456"

background.py: PlaneSyncLoop
  → voor elk geregistreerd project:
       als sync_enabled: import_cycle(project_dir, cycle_id)
```

### Implementatieplan

1. **Registry keys uitbreiden:** `plane_*` settings krijgen een `:project_name` suffix
   - `get_setting("plane_cycle_id")` → `get_setting("plane_cycle_id:klaverjas_app")`
   - Backward-compat: als key zonder suffix bestaat, gebruik die als fallback

2. **Sync loop per-project:** `PlaneSyncLoop._poll()` itereert over `list_registered_projects()`, leest per-project config, en sync't alleen projecten met `plane_sync_enabled:X = true`

3. **API endpoints:** `GET/POST /api/plane/config` krijgen optionele `?project_name=X` parameter
   - Zonder param: legacy gedrag (globale config)
   - Met param: project-specifieke config

4. **UI:** SettingsModal Plane sectie toont config per geselecteerd project

5. **Migratie:** bij eerste start na update, kopieer globale `plane_*` settings naar het eerste geregistreerde project

### Alternatieven overwogen

| Alternatief | Reden afgewezen |
|---|---|
| Plane config in `features.db` per project | Mixen van concerns: features.db is voor feature data, niet configuratie |
| Aparte config file per project (`.autoforge/plane.json`) | Inconsistent met bestaand registry pattern |
| Project-specifieke DB tabel in registry.db | Overkill — registry key suffix is eenvoudiger |

## Gevolgen

- Meerdere projecten kunnen tegelijk met Plane sync draaien
- Elk project koppelt aan zijn eigen Plane workspace/project/cycle
- Geen cross-project data lekkage meer
- Bestaande single-project setups blijven werken (migratie)
