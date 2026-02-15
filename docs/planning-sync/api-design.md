# MQ Planning Sync API Design

## Overzicht

Nieuwe API router `/api/planning/` voor alle MQ Planning-gerelateerde operaties.

## Endpoints

### Configuratie

#### `GET /api/planning/config`

Huidige MQ Planning configuratie ophalen. API key wordt gemaskeerd.

**Response:**
```json
{
  "planning_api_url": "http://localhost:8080",
  "planning_api_key_set": true,
  "planning_api_key_masked": "planning_api_****xxxx",
  "planning_workspace_slug": "my-workspace",
  "planning_project_id": "550e8400-e29b-41d4-a716-446655440000",
  "planning_sync_enabled": false,
  "planning_poll_interval": 30,
  "planning_active_cycle_id": null,
  "planning_webhook_secret_set": false
}
```

#### `POST /api/planning/config`

MQ Planning configuratie bijwerken.

**Request:**
```json
{
  "planning_api_url": "http://localhost:8080",
  "planning_api_key": "plane_api_xxxxxxxxxxxx",
  "planning_workspace_slug": "my-workspace",
  "planning_project_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:** `200 OK` met bijgewerkte config (gemaskeerde key).

### Verbinding

#### `POST /api/planning/test-connection`

Test de verbinding met MQ Planning API. Verifieert API key, workspace en project.

**Response (succes):**
```json
{
  "status": "ok",
  "workspace": "my-workspace",
  "project_name": "MQ DevEngine Project",
  "planning_version": "0.23"
}
```

**Response (fout):**
```json
{
  "status": "error",
  "message": "Invalid API key",
  "details": "HTTP 401 from MQ Planning API"
}
```

### Cycles

#### `GET /api/planning/cycles`

Beschikbare cycles (sprints) ophalen uit MQ Planning.

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

#### `POST /api/planning/import-cycle`

Importeer work items uit een MQ Planning cycle als Features.

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
      "planning_id": "work-item-uuid-1",
      "name": "Add OAuth2 login",
      "action": "created",
      "feature_id": 15
    },
    {
      "planning_id": "work-item-uuid-2",
      "name": "Fix login bug",
      "action": "skipped",
      "reason": "already_imported"
    }
  ]
}
```

**Logica:**
1. Haal alle work items op uit de cycle via MQ Planning API
2. Filter: skip cancelled items
3. Voor elk work item:
   - Als `planning_work_item_id` al bestaat in Feature DB -> update (als MQ Planning nieuwer is)
   - Als niet bestaat -> maak nieuwe Feature aan
4. Map priority, state, category, dependencies
5. Sla `planning_work_item_id` en `planning_synced_at` op

### Sync Status

#### `GET /api/planning/sync-status`

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

#### `POST /api/planning/sync/toggle`

Toggle de background sync loop aan/uit.

**Response:** Zelfde als `GET /api/planning/sync-status`.

### Sprint Completion

#### `POST /api/planning/complete-sprint`

Complete de huidige sprint: DoD verificatie, retrospective naar MQ Planning, git tag, release notes.

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

#### `GET /api/planning/test-report?project_name=X&all_features=true`

Geaggregeerd test rapport voor features in een project. Standaard alleen MQ Planning-gelinkte features; met `all_features=true` alle features.

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

#### `GET /api/planning/test-history?project_name=X&feature_id=N&limit=50`

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

#### `GET /api/planning/release-notes?project_name=X`

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

#### `GET /api/planning/release-notes/content?project_name=X&filename=Y`

Inhoud van een specifiek release notes bestand. Beschermd tegen path traversal.

**Response:**
```json
{
  "filename": "sprint-sprint-5.md",
  "content": "# Sprint 5 Release Notes\n\n..."
}
```

### Webhooks

#### `POST /api/planning/webhooks`

Ontvang webhook events van MQ Planning. HMAC-SHA256 verificatie indien geconfigureerd.

**Beveiliging:**
- Exempt van localhost middleware (HMAC is de authenticatie)
- Als `planning_webhook_secret` is geconfigureerd, wordt de signature geverifieerd
- Event dedup: zelfde event key wordt 5 seconden genegeerd

**Headers:**
```
X-Planning-Signature: <hmac-sha256-hex>
```

**Request body:** MQ Planning webhook payload (JSON).

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

#### `POST /api/planning/self-host-setup`

Registreer MQ DevEngine als project in eigen registry (idempotent).

**Response:**
```json
{
  "project_name": "mq-devengine",
  "project_path": "/home/user/Projects/mq-devEngine",
  "already_registered": false
}
```

**Logica:**
1. Detecteer MQ DevEngine project root via marker files (`server/main.py`, `parallel_orchestrator.py`, `planning_sync/__init__.py`)
2. Registreer in `~/.mq-devengine/registry.db` via `register_project()`
3. Idempotent: tweede call returnt `already_registered: true`

### MarQed Import

#### `POST /api/planning/marqed-import`

Importeer een MarQed markdown directory tree als MQ Planning modules en work items.

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
      "planning_type": "module",
      "planning_id": "module-uuid-1",
      "action": "created",
      "error": ""
    },
    {
      "identifier": "FEATURE-001",
      "name": "Login Form",
      "entity_type": "feature",
      "planning_type": "work_item",
      "planning_id": "work-item-uuid-1",
      "action": "created",
      "error": ""
    }
  ]
}
```

**Import algoritme:**
1. `parse_marqed_tree(dir)` -> entity tree
2. `list_states()` van MQ Planning voor status mapping
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

Sinds Sprint 7.1 ondersteunen alle config- en sync-endpoints een optionele `project_name` parameter voor per-project MQ Planning configuratie.

**Per-project settings:** `planning_project_id`, `planning_active_cycle_id`, `planning_sync_enabled`, `planning_poll_interval`
**Gedeelde settings:** `planning_api_url`, `planning_api_key`, `planning_workspace_slug`, `planning_webhook_secret`

| Endpoint | Parameter | Methode |
|---|---|---|
| `GET /api/planning/config` | `?project_name=X` | Query param |
| `POST /api/planning/config` | `project_name` in body | Body field |
| `POST /api/planning/test-connection` | `?project_name=X` | Query param |
| `GET /api/planning/cycles` | `?project_name=X` | Query param |
| `GET /api/planning/sync-status` | `?project_name=X` | Query param |
| `POST /api/planning/sync/toggle` | `?project_name=X` | Query param |

Zonder `project_name` parameter: fallback naar globale config (backward compatible).

Zie [ADR-004](../decisions/ADR-004-per-project-plane-sync.md).

## Authenticatie

MQ Planning API endpoints in MQ DevEngine zijn beschermd door dezelfde auth als de rest van de server (indien geconfigureerd). De MQ Planning API key wordt alleen server-side gebruikt en nooit naar de frontend gestuurd (alleen gemaskeerde versie).

## Error Handling

| HTTP Status | Betekenis |
|---|---|
| 200 | Succes |
| 400 | Ongeldige request (missing fields, invalid cycle_id) |
| 401 | MQ Planning API key ongeldig of niet geconfigureerd |
| 404 | Cycle of project niet gevonden in MQ Planning |
| 429 | MQ Planning rate limit bereikt |
| 502 | MQ Planning API niet bereikbaar |

## Rate Limiting

- MQ Planning API: 60 req/min
- Polling budget: ~14 req/min (30s interval, 2-3 calls per poll)
- Import burst: max 50 req/min bij grote import (laat 10 req/min over)
- Backoff: exponential bij 429 responses
