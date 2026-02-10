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

#### `GET /api/plane/test-report?project_name=X`

Geaggregeerd test rapport voor alle Plane-gelinkte features in een project.

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
