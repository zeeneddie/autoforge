# Plane Sync API Design

## Overzicht

Nieuwe API router `/api/plane/` voor alle Plane-gerelateerde operaties.

## Endpoints

### Configuratie

#### `GET /api/plane/config`

Huidige Plane configuratie ophalen. API key wordt gemaskeerd.

**Response:**
```json
{
  "plane_api_url": "http://localhost:8080",
  "plane_api_key_set": true,
  "plane_api_key_masked": "plane_api_****xxxx",
  "plane_workspace_slug": "my-workspace",
  "plane_project_id": "550e8400-e29b-41d4-a716-446655440000",
  "plane_sync_enabled": false,
  "plane_poll_interval": 30,
  "plane_active_cycle_id": null,
  "plane_webhook_secret_set": false
}
```

#### `POST /api/plane/config`

Plane configuratie bijwerken.

**Request:**
```json
{
  "plane_api_url": "http://localhost:8080",
  "plane_api_key": "plane_api_xxxxxxxxxxxx",
  "plane_workspace_slug": "my-workspace",
  "plane_project_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:** `200 OK` met bijgewerkte config (gemaskeerde key).

### Verbinding

#### `POST /api/plane/test-connection`

Test de verbinding met Plane API. Verifieert API key, workspace en project.

**Response (succes):**
```json
{
  "status": "ok",
  "workspace": "my-workspace",
  "project_name": "AutoForge Project",
  "plane_version": "0.23"
}
```

**Response (fout):**
```json
{
  "status": "error",
  "message": "Invalid API key",
  "details": "HTTP 401 from Plane API"
}
```

### Cycles

#### `GET /api/plane/cycles`

Beschikbare cycles (sprints) ophalen uit Plane.

**Response:**
```json
{
  "cycles": [
    {
      "id": "cycle-uuid-1",
      "name": "Sprint 4",
      "start_date": "2026-02-10",
      "end_date": "2026-02-16",
      "status": "current",
      "total_issues": 8,
      "completed_issues": 3
    },
    {
      "id": "cycle-uuid-2",
      "name": "Sprint 5",
      "start_date": "2026-02-17",
      "end_date": "2026-02-23",
      "status": "upcoming",
      "total_issues": 0,
      "completed_issues": 0
    }
  ]
}
```

### Import

#### `POST /api/plane/import-cycle`

Importeer work items uit een Plane cycle als Features.

**Request:**
```json
{
  "cycle_id": "cycle-uuid-1",
  "project_name": "my-project"
}
```

**Response:**
```json
{
  "imported": 5,
  "skipped": 2,
  "updated": 1,
  "details": [
    {
      "plane_id": "work-item-uuid-1",
      "name": "Add OAuth2 login",
      "action": "created",
      "feature_id": 15
    },
    {
      "plane_id": "work-item-uuid-2",
      "name": "Fix login bug",
      "action": "skipped",
      "reason": "already_imported"
    }
  ]
}
```

**Logica:**
1. Haal alle work items op uit de cycle via Plane API
2. Filter: skip cancelled items
3. Voor elk work item:
   - Als `plane_work_item_id` al bestaat in Feature DB -> update (als Plane nieuwer is)
   - Als niet bestaat -> maak nieuwe Feature aan
4. Map priority, state, category, dependencies
5. Sla `plane_work_item_id` en `plane_synced_at` op

### Sync Status

#### `GET /api/plane/sync-status`

Status van de sync service.

**Response:**
```json
{
  "enabled": true,
  "running": true,
  "last_sync_at": "2026-02-10T14:30:00Z",
  "last_error": null,
  "items_synced": 3,
  "active_cycle_name": "Sprint 5",
  "sprint_complete": false,
  "sprint_stats": {
    "total": 8,
    "passing": 6,
    "failed": 2,
    "total_test_runs": 42,
    "overall_pass_rate": 85.7
  },
  "last_webhook_at": "2026-02-10T14:29:55Z",
  "webhook_count": 12
}
```

### Sync Control

#### `POST /api/plane/sync/toggle`

Toggle de background sync loop aan/uit.

**Response:** Zelfde als `GET /api/plane/sync-status`.

### Sprint Completion

#### `POST /api/plane/complete-sprint`

Complete de huidige sprint: DoD verificatie, retrospective naar Plane, git tag, release notes.

**Request:**
```json
{
  "project_name": "my-project"
}
```

**Response:**
```json
{
  "success": true,
  "features_completed": 8,
  "features_failed": 0,
  "git_tag": "sprint/sprint-5",
  "change_log": "abc1234 feat: add OAuth2 login\ndef5678 fix: token refresh",
  "release_notes_path": "/path/to/project/releases/sprint-sprint-5.md",
  "error": null
}
```

### Test Report

#### `GET /api/plane/test-report?project_name=X&all_features=true`

Geaggregeerd test rapport voor features in een project. Standaard alleen Plane-gelinkte features; met `all_features=true` alle features.

**Response:**
```json
{
  "total_features": 8,
  "features_tested": 6,
  "features_never_tested": 2,
  "total_test_runs": 42,
  "overall_pass_rate": 85.7,
  "feature_summaries": [
    {
      "feature_id": 1,
      "feature_name": "OAuth2 login",
      "total_runs": 8,
      "pass_count": 7,
      "fail_count": 1,
      "last_tested_at": "2026-02-10T14:30:00",
      "last_result": true
    }
  ],
  "generated_at": "2026-02-10T14:30:00Z"
}
```

### Test History

#### `GET /api/plane/test-history?project_name=X&feature_id=N&limit=50`

Individuele TestRun records voor timeline/heatmap weergave. `feature_id` en `limit` zijn optioneel.

**Response:**
```json
{
  "runs": [
    {
      "id": 42,
      "feature_id": 1,
      "feature_name": "OAuth2 login",
      "passed": true,
      "agent_type": "testing",
      "completed_at": "2026-02-10T14:30:00",
      "return_code": 0
    }
  ],
  "total_count": 42
}
```

### Release Notes

#### `GET /api/plane/release-notes?project_name=X`

Lijst van beschikbare release notes bestanden in `{project}/releases/`.

**Response:**
```json
{
  "items": [
    {
      "filename": "sprint-sprint-5.md",
      "cycle_name": "Sprint 5",
      "created_at": "2026-02-10T14:30:00Z",
      "size_bytes": 2048
    }
  ]
}
```

#### `GET /api/plane/release-notes/content?project_name=X&filename=Y`

Inhoud van een specifiek release notes bestand. Beschermd tegen path traversal.

**Response:**
```json
{
  "filename": "sprint-sprint-5.md",
  "content": "# Sprint 5 Release Notes\n\n..."
}
```

### Webhooks

#### `POST /api/plane/webhooks`

Ontvang webhook events van Plane. HMAC-SHA256 verificatie indien geconfigureerd.

**Beveiliging:**
- Exempt van localhost middleware (HMAC is de authenticatie)
- Als `plane_webhook_secret` is geconfigureerd, wordt de signature geverifieerd
- Event dedup: zelfde event key wordt 5 seconden genegeerd

**Headers:**
```
X-Plane-Signature: <hmac-sha256-hex>
```

**Request body:** Plane webhook payload (JSON).

**Response:**
```json
{
  "status": "ok",
  "action": "processed"
}
```

**Acties per event:**
- `issue.update` / `work_item.update` -> `import_cycle()` voor actieve cycle
- `cycle.update` (matching cycle ID) -> `import_cycle()` voor actieve cycle

**Mogelijke response actions:** `"processed"`, `"deduped"`, `"no_active_cycle"`, `"error"`

### Self-Hosting

#### `POST /api/plane/self-host-setup`

Registreer AutoForge als project in eigen registry (idempotent).

**Response:**
```json
{
  "project_name": "autoforge",
  "project_path": "/home/user/Projects/autoforge",
  "already_registered": false
}
```

**Logica:**
1. Detecteer AutoForge project root via marker files (`server/main.py`, `parallel_orchestrator.py`, `plane_sync/__init__.py`)
2. Registreer in `~/.autoforge/registry.db` via `register_project()`
3. Idempotent: tweede call returnt `already_registered: true`

### MarQed Import

#### `POST /api/plane/marqed-import`

Importeer een MarQed markdown directory tree als Plane modules en work items.

**Request:**
```json
{
  "marqed_dir": "/path/to/marqed/project",
  "cycle_id": "cycle-uuid-1"
}
```

`cycle_id` is optioneel. Als opgegeven worden alle work items aan de cycle toegevoegd.

**Response:**
```json
{
  "total_entities": 6,
  "created": 6,
  "errors": 0,
  "modules_created": 1,
  "work_items_created": 5,
  "entities": [
    {
      "identifier": "EPIC-001",
      "name": "Authentication",
      "entity_type": "epic",
      "plane_type": "module",
      "plane_id": "module-uuid-1",
      "action": "created",
      "error": ""
    },
    {
      "identifier": "FEATURE-001",
      "name": "Login Form",
      "entity_type": "feature",
      "plane_type": "work_item",
      "plane_id": "work-item-uuid-1",
      "action": "created",
      "error": ""
    }
  ]
}
```

**Import algoritme:**
1. `parse_marqed_tree(dir)` -> entity tree
2. `list_states()` van Plane voor status mapping
3. Per epic: `create_module()` -> module_id
4. Per feature: `create_work_item()` -> work_item_id, link to module
5. Per story: `create_work_item(parent=feature_id)` -> sub_work_item_id
6. Per task: `create_work_item(parent=story_id)` -> sub_work_item_id
7. `add_work_items_to_module()` per module
8. `add_work_items_to_cycle()` als cycle_id opgegeven

**Rate limiting:** ~68 API calls voor typische import (3 epics, 10 features, 20 stories, 30 tasks) = ~102s bij 1.5s interval.

### Agent Soft Stop

#### `POST /api/projects/{project_name}/agent/soft-stop`

Graceful agent shutdown: agents ronden lopend werk af, claimen geen nieuwe features.

**Response:**
```json
{
  "success": true,
  "status": "finishing",
  "message": "Soft stop initiated, agents finishing current work"
}
```

**Status flow:** `running` → `finishing` → `stopped` (automatisch na afronding).

De orchestrator ontvangt `SIGUSR1`, zet `_shutdown_requested=True` maar houdt `is_running=True`. Lopende agents worden niet onderbroken. Na afronding stopt het process met exit code 0.

Hard stop (`POST /api/projects/{name}/agent/stop`) blijft beschikbaar als noodknop vanuit elke state, inclusief `finishing`.

---

## Per-Project Configuratie

Sinds Sprint 7.1 ondersteunen alle config- en sync-endpoints een optionele `project_name` parameter voor per-project Plane configuratie.

**Per-project settings:** `plane_project_id`, `plane_active_cycle_id`, `plane_sync_enabled`, `plane_poll_interval`
**Gedeelde settings:** `plane_api_url`, `plane_api_key`, `plane_workspace_slug`, `plane_webhook_secret`

| Endpoint | Parameter | Methode |
|---|---|---|
| `GET /api/plane/config` | `?project_name=X` | Query param |
| `POST /api/plane/config` | `project_name` in body | Body field |
| `POST /api/plane/test-connection` | `?project_name=X` | Query param |
| `GET /api/plane/cycles` | `?project_name=X` | Query param |
| `GET /api/plane/sync-status` | `?project_name=X` | Query param |
| `POST /api/plane/sync/toggle` | `?project_name=X` | Query param |

Zonder `project_name` parameter: fallback naar globale config (backward compatible).

Zie [ADR-004](../decisions/ADR-004-per-project-plane-sync.md).

## Authenticatie

Plane API endpoints in AutoForge zijn beschermd door dezelfde auth als de rest van de server (indien geconfigureerd). De Plane API key wordt alleen server-side gebruikt en nooit naar de frontend gestuurd (alleen gemaskeerde versie).

## Error Handling

| HTTP Status | Betekenis |
|---|---|
| 200 | Succes |
| 400 | Ongeldige request (missing fields, invalid cycle_id) |
| 401 | Plane API key ongeldig of niet geconfigureerd |
| 404 | Cycle of project niet gevonden in Plane |
| 429 | Plane rate limit bereikt |
| 502 | Plane API niet bereikbaar |

## Rate Limiting

- Plane API: 60 req/min
- Polling budget: ~14 req/min (30s interval, 2-3 calls per poll)
- Import burst: max 50 req/min bij grote import (laat 10 req/min over)
- Backoff: exponential bij 429 responses
