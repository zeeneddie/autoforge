# Sprint 7.3: Stuck-State Detection & LLM-Assisted Recovery + Functionele Model Tiers

> Status: DONE
> Prioriteit: HIGH — lost een blokkerend probleem op waarbij de orchestrator eindeloos wacht
> Afhankelijkheden: geen (bouwt op bestaande parallel_orchestrator.py)

## Probleem 1: Stuck State

Wanneer features permanent falen (na 3 pogingen), worden afhankelijke features permanent geblokkeerd. De orchestrator logt dan eindeloos "No ready features available" zonder actie. Dit verspilt resources en vereist handmatig ingrijpen.

## Probleem 2: Anthropic merknamen in code

De code gebruikt `"opus"`, `"sonnet"`, `"haiku"` als model tier namen. Dit zijn Anthropic merknamen die niets zeggen over functionaliteit. Bij een provider-switch (OpenAI, DeepSeek) worden deze namen betekenisloos.

## Oplossing 1: Stuck-State Recovery

Intelligent recovery-systeem met auto-recovery bij hoge confidence:
- **>= 0.8 confidence** → automatisch uitvoeren (geen human-in-the-loop)
- **< 0.8 confidence** → human-in-the-loop via UI modal
- **skip/stop** → altijd human (scope-beslissingen)
- **max 2x auto-recovery** achter elkaar → daarna sowieso human

## Oplossing 2: Functionele Model Tiers

Vervang Anthropic merknamen door functionele capability namen:

| Oud (merknaam) | Nieuw (functioneel) | Betekenis |
|---|---|---|
| `"opus"` | `"analyst"` | Maximale capability, diepe analyse, complexe architectuur |
| `"sonnet"` | `"developer"` | Default workhorse, coding taken (fallback tier) |
| `"haiku"` | `"assistant"` | Snelle lichte taken, orchestratie, classificatie |

---

## Fase 0: Functionele Model Tiers (Rename)

> Bestanden: `task_router.py`, `provider_config.py`, `providers.json`, `parallel_orchestrator.py`, `test_sdk_minimal.py`

- [x] **0.1** `task_router.py`: `ModelTier = Literal["analyst", "developer", "assistant"]` (was `opus`/`sonnet`/`haiku`)
- [x] **0.2** `task_router.py`: hele `ROUTING_TABLE` omzetten naar functionele namen
- [x] **0.3** `task_router.py`: `DEFAULT_MODEL_TIERS` keys renamen (`"analyst"` → model, `"developer"` → model, `"assistant"` → model)
- [x] **0.4** `task_router.py`: fallback default van `"sonnet"` → `"developer"`
- [x] **0.5** `provider_config.py`: `DEFAULT_PROVIDERS` model_tiers keys renamen in alle 4 provider profiles
- [x] **0.6** `provider_config.py`: docstrings en return type hints updaten
- [x] **0.7** `task_router.py`: `_LEGACY_TIER_MAP` + `normalize_tier()` + backward compat in `resolve_model_tier()` voor bestaande providers.json met oude keys
- [x] **0.8** `parallel_orchestrator.py`: geen directe tier referenties (gebruikt task_router)
- [x] **0.9** `test_sdk_minimal.py`: `"sonnet"` → `"developer"`
- [x] **0.10** Env variabelen: `ANTHROPIC_DEFAULT_OPUS_MODEL` etc. blijven werken (provider_config leest die los van tiers)

### Checkpoint Fase 0: DONE
Alle interne code gebruikt `analyst`/`developer`/`assistant`. Backward compat via `normalize_tier()` en `resolve_model_tier()`.

---

## Fase 1: Stuck-State Detectie (Backend)

> Bestanden: `parallel_orchestrator.py`, `devengine_paths.py`

- [x] **1.1** `devengine_paths.py`: nieuwe helper `get_stuck_state_path(project_dir) -> Path`
- [x] **1.2** `parallel_orchestrator.py` `__init__()`: nieuwe state tracking
  - `_no_progress_iterations: int = 0`
  - `_stuck_state_active: bool = False`
  - `_auto_recovery_count: int = 0`
- [x] **1.3** Reset `_no_progress_iterations = 0` in `start_feature()`, `start_feature_batch()`, en `_on_agent_complete()`
- [x] **1.4** `_detect_stuck_state(feature_dicts)` methode met BFS
- [x] **1.5** Integratie in `run_loop`: na `_no_progress_iterations >= 3` → check stuck state

### Checkpoint Fase 1: DONE

---

## Fase 2: LLM Analyse

> Bestanden: `stuck_analyzer.py` (nieuw)

- [x] **2.1** `analyze_stuck_state()` async functie met structured JSON output
- [x] **2.2** Context naar LLM: app spec, feature status, dependency graph, agent logs
- [x] **2.3** Prompt inline in `_build_prompt()` (geen apart template nodig — prompt is code, niet configureerbaar)
- [x] **2.4** Fallback bij LLM-fout: basic report zonder suggesties, recommended_option = "stop", confidence = 0.0
- [x] **2.5** Gebruikt `claude` CLI als subprocess (consistent met rest van project)
- [x] **2.6** `_parse_response()` met robuuste JSON extractie (direct, code blocks, brace matching)

### Checkpoint Fase 2: DONE

---

## Fase 3: Auto-Recovery & Human-in-the-Loop (API + WebSocket)

> Bestanden: `server/routers/stuck_state.py` (nieuw), `server/routers/__init__.py`, `server/main.py`, `server/schemas.py`, `server/websocket.py`

### Auto-recovery logica (in parallel_orchestrator.py)
- [x] **3.1** `_handle_stuck_state()`: auto-recovery check (confidence >= 0.8, niet skip/stop, count < 2)
- [x] **3.2** Auto-execute path met logging
- [x] **3.3** Human path: schrijf `stuck_state.json`, poll elke 2s

### IPC: stuck_state.json
- [x] **3.4** File format geïmplementeerd

### API endpoints
- [x] **3.5** `GET /api/projects/{name}/stuck-state` → 200 met data, of 404
- [x] **3.6** `POST /api/projects/{name}/stuck-state/decision` → schrijft decision
- [x] **3.7** Router registratie in `__init__.py` en `main.py`

### Pydantic schemas
- [x] **3.8** `StuckStateResponse`, `StuckDecisionRequest`, `StuckSuggestion` in `server/schemas.py`

### WebSocket integratie
- [x] **3.9** Nieuwe patterns: `stuck_analyzing`, `stuck_awaiting`, `stuck_resolved`, `stuck_auto_recovery`
- [x] **3.10** State `'stuck'` op `OrchestratorTracker` met handlers

### Checkpoint Fase 3: DONE

---

## Fase 4: Recovery Opties — Decision Handling

> Bestanden: `parallel_orchestrator.py`

### STOP
- [x] **4.1** `_handle_stuck_decision()` met stop → `is_running = False`

### RETRY
- [x] **4.2** `_retry_failed_features()`: reset failure counts + clear in_progress

### MODIFY
- [x] **4.3** `_apply_modifications()` met `modify_feature`: update description/steps, reset failure count
- [x] **4.4** `remove_dependency`: verwijder dependency uit feature
- [x] **4.5** `skip_feature`: verwijder als dependency van alle features, markeer als permanent overgeslagen

### Na elke recovery-actie
- [x] **4.6** session.commit(), state reset, stuck_state.json cleanup

### Checkpoint Fase 4: DONE

---

## Fase 5: UI Component

> Bestanden: `ui/src/components/StuckStateModal.tsx` (nieuw), `ui/src/lib/types.ts`, `ui/src/lib/api.ts`, `ui/src/App.tsx`

- [x] **5.1** TypeScript types: `StuckStateData`, `StuckSuggestion` in `types.ts` + `OrchestratorState` met `'stuck'`
- [x] **5.2** WebSocket: `orchestratorStatus.state === 'stuck'` triggert modal via bestaande hook
- [x] **5.3** `StuckStateModal.tsx`: neobrutalism design met alle geplande secties
- [x] **5.4** Auto-recovery toast: TODO (kan later als aparte verbetering)
- [x] **5.5** Integratie in App.tsx: modal gerenderd bij stuck state
- [x] **5.6** API functies: `getStuckState()`, `submitStuckDecision()` in `api.ts`

### Checkpoint Fase 5: DONE

---

## Config

Configureerbaar via hardcoded constanten in `parallel_orchestrator.py`:
- `MAX_FEATURE_RETRIES = 3` (detectie threshold)
- `_auto_recovery_count < 2` (max auto-recoveries)
- `confidence >= 0.8` (auto-recovery drempel)
- skip/stop altijd human

---

## Verificatie

1. **Detectie:** Project met feature A (geen deps) en B (depends A). A faalt 3x → stuck detectie na ~30s
2. **LLM analyse:** `analyze_stuck_state()` retourneert valide JSON met suggesties
3. **Auto-recovery:** Suggestie met confidence >= 0.8 (retry) wordt automatisch uitgevoerd
4. **Human-in-the-loop:** Suggestie met confidence < 0.8 → UI modal verschijnt
5. **Max auto-recovery:** Na 2x auto-recovery → volgende stuck gaat naar human
6. **API:** GET stuck-state → 200, POST decision met retry → features gereset
7. **UI:** Modal verschijnt, kies retry → engine gaat verder
8. **Edge cases:** LLM timeout (fallback), browser sluiten (file persists), skip altijd human

---

## Gewijzigde bestanden

| Bestand | Actie | Doel |
|---------|-------|------|
| `task_router.py` | MODIFIED | Functionele tiers (analyst/developer/assistant) + backward compat |
| `provider_config.py` | MODIFIED | Functionele tier keys in DEFAULT_PROVIDERS |
| `test_sdk_minimal.py` | MODIFIED | `"sonnet"` → `"developer"` |
| `devengine_paths.py` | MODIFIED | `get_stuck_state_path()` helper |
| `parallel_orchestrator.py` | MODIFIED | Detectie, state mgmt, auto-recovery, decision handling |
| `stuck_analyzer.py` | CREATED | LLM analyse via claude CLI |
| `server/routers/stuck_state.py` | CREATED | GET/POST endpoints |
| `server/routers/__init__.py` | MODIFIED | Router registratie |
| `server/main.py` | MODIFIED | Router include |
| `server/schemas.py` | MODIFIED | Pydantic schemas |
| `server/websocket.py` | MODIFIED | Stuck patterns + tracker states |
| `ui/src/lib/types.ts` | MODIFIED | StuckStateData types + OrchestratorState 'stuck' |
| `ui/src/lib/api.ts` | MODIFIED | getStuckState, submitStuckDecision |
| `ui/src/components/StuckStateModal.tsx` | CREATED | UI modal component |
| `ui/src/App.tsx` | MODIFIED | Modal integratie |
| `docs/roadmap.md` | MODIFIED | Sprint 7.3 toegevoegd, 7.3-7.7 verschoven naar 7.4-7.8 |
