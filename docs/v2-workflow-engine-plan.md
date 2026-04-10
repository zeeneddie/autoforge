# MQ DevEngine v2 — Workflow-Driven Agent Orchestration

## Context

DevEngine v1 stuurt coding agents aan met een mega-prompt van ~200 regels per feature. De agent moet zelf bepalen wat hij doet, in welke volgorde, en kan validatiestappen overslaan. De UI toont alleen tool-calls (het HOW), niet de goals/stappen (het WHAT). 

Geinspireerd door Archon's harness-engineering approach bouwen we v2: **YAML-gedefinieerde workflows** die de feature-implementatie opsplitsen in expliciete, trackbare stappen -- met deterministische validatie-nodes die de orchestrator uitvoert (niet de LLM). De workflow-stappen worden de "goals" in een nieuwe stepper + accordeon UI.

Planning_sync (mq-planning bidirectionele sync) wordt meegenomen in v2 scope.

### Kernargumenten voor v2

1. **Deterministische stappen kan de agent NIET overslaan** — lint, test, mock-check worden subprocessen van de orchestrator
2. **Gefocuste prompts per stap = betere resultaten** — 5x 30 regels > 1x 200 regels
3. **Fresh context per stap = geen vervuiling** — review in schone sessie, zonder bias van implementatie
4. **Goals View gratis** — workflow-stappen ZIJN de goals, geen apart tracking systeem nodig
5. **Model-per-stap** — haiku voor verkenning/review, sonnet/opus voor coderen

### Inspiratie: Archon (coleam00/Archon)

Archon is een open-source harness builder voor AI coding. Concepten die we overnemen:
- YAML-gedefinieerde workflows als DAG van nodes
- Twee node types: prompt (LLM sessie) en deterministic (subprocess)
- Model keuze per node
- Fresh session vs continued conversation per node
- Web UI met workflow visualisatie

Wat we NIET overnemen:
- Archon's YAML DSL syntax (we maken ons eigen schema)
- Aparte workflow runner (we integreren in bestaande orchestrator)
- Context window management per node (we doen dit al goed met fresh sessions + memory MCP)

---

## Huidige Flow (v1) — Visueel

```
MQ PLANNING (mq-planning)
  Cycle "Sprint 7"
  +-- Epic 1: User Management
  |   +-- Story 1.1: Login flow           <-- work items met AC's
  |   +-- Story 1.2: Registration
  |   +-- Story 1.3: Password reset
  +-- Epic 2: Dashboard
      +-- Story 2.1: Analytics widget
      +-- Story 2.2: Activity feed
         |
         | REST API (mq-planning -> DevEngine)
         | planning_sync/sync_service.py::import_cycle()
         v
MQ DEVENGINE -- Features DB
  Feature 1: "Login flow"        steps: ["user can login", "session persists"]
  Feature 2: "Registration"      steps: ["form validates", "email sent"]
  Feature 3: "Password reset"    steps: [...]
  Feature 4: "Analytics widget"  steps: [...]
  Feature 5: "Activity feed"     steps: [...]
  (dependencies automatisch geketend: 1->2->3, 4->5)
         |
         | parallel_orchestrator.py::run_loop()
         v
PHASE 0: ARCHITECT (optioneel)
  Leest app_spec.txt, slaat architecture decisions op in memory
         |
         v
PHASE 1: STORY PLANNER (per feature)
  Input: Feature beschrijving + AC's + architecture memory
  Output: feature_create_sub_features()
  
  Feature 1: "Login flow"
  +-- 1.1 DB session tabel
  +-- 1.2 Auth endpoint
  +-- 1.3 JWT tokens
  +-- 1.4 Login UI
  +-- 1.5 E2E tests
  (sequentieel geketend: 1.1 -> 1.2 -> 1.3 -> ...)
         |
         | Sync sub-features naar mq-planning
         v
PHASE 2: CODING AGENTS (max 5 parallel)       <-- HIER ZIT HET PROBLEEM
  Agent "Spark" -- Feature 1.1 "DB session tabel"
  Agent "Fizz"  -- Feature 4   "Analytics widget"
  Agent "Octo"  -- Feature 1.2 "Auth endpoint"  (wacht op 1.1)
  
  Elke agent krijgt: coding_prompt.template.md (200 regels instructies)
  Agent moet ZELF:
    x Volgorde bepalen
    x Testen draaien (kan vergeten)
    x Lint checken (kan overslaan)
    x Mock data vermijden (kan falen)
    x Zelf-reviewen (doet het niet)
  
  -> feature_mark_passing()
  -> feature_submit_for_review()
         |
    +----+----+
    v         v
PHASE 3: TESTING     PHASE 4: REVIEW
  (parallel, onafh.)   (optioneel)
  Draait AC stappen    Code quality check
  Detecteert mock data Mock data grep
  Regressie tests      Spec compliance
                       -> approve / reject
         |
         v
OUTBOUND SYNC -> mq-planning
  Feature passes=true  -> mq-planning state: "completed"
  Feature in_progress  -> mq-planning state: "started"
  Feature rejected     -> mq-planning state: "blocked" + comment
  Sub-feature status   -> Aggregated op parent in mq-planning
```

---

## Nieuwe Flow (v2) — Workflow-Driven

Phase 2 verandert fundamenteel. In plaats van een mega-prompt wordt elke sub-feature een **YAML workflow**:

```
PHASE 2 (v2): FEATURE WORKFLOW -- gestuurd door workflow.yaml

Per sub-feature (bv. 1.2 "Auth endpoint"):

  [explore]-->[plan]-->[implement]-->[lint]-->[mock_check]-->[test]-->[server_restart]-->[review]
   (haiku)   (sonnet)   (sonnet)     (bash)    (bash)       (bash)     (bash)          (haiku)
    LLM        LLM        LLM        DET.       DET.         DET.       DET.            LLM

  LLM  = coding agent sessie (gefocuste prompt, ~30 regels)
  DET. = orchestrator subprocess (NIET de LLM, KAN NIET overslaan)

  Dit is wat je ZIET in de UI:

  Feature 1.2: "Auth endpoint"
  V Explore        2 min
  V Plan           3 min
  > Implement      <-- agent is hier
  o Lint           wacht
  o Mock Check     wacht
  o Test           wacht
  o Server Restart wacht
  o Review         wacht
```

---

## Stap 0: v1 Afsluiting

**Doel**: Clean break -- alles mergen naar master, taggen als v1.

1. **Commit uncommitted changes** op `feature/sprint-7.3-stuck-state-recovery`:
   - 8 modified files: `client.py`, `mcp_server/feature_mcp.py`, `parallel_orchestrator.py`, `planning_sync/__init__.py`, `planning_sync/completion.py`, `planning_sync/models.py`, `role_registry.py`, `server/routers/planning.py`
   - 7 untracked files: `docs/adversarial-evaluator-plan.md`, `planning_sync/demo_capture.py`, `planning_sync/demo_seed.py`, `planning_sync/narrative_renderer.py`, `planning_sync/report_generator.py`, `planning_sync/screenshot_validator.py`, `projects/`
   - **Niet committen**: `mq_devengine.db` (runtime artifact)

2. **Merge naar master**: `feature/sprint-7.3-stuck-state-recovery` -> master
   - Check of `feature/aggregated-plane-sync` (1 commit) ook mee moet

3. **Tag**: `git tag v1.0.0` op master

4. **Nieuwe branch**: `git checkout -b v2/workflow-engine` vanaf master

---

## Stap 1: YAML Workflow Schema

**Doel**: Definieer het YAML-formaat voor feature workflows.

### Bestanden
- **Nieuw**: `workflow/schema.py` -- Pydantic modellen voor workflow parsing + validatie
- **Nieuw**: `workflow/defaults/standard.yaml` -- Standaard workflow
- **Nieuw**: `workflow/defaults/yolo.yaml` -- Snelle workflow (implement -> lint)
- **Nieuw**: `workflow/defaults/minimal.yaml` -- Zonder story-planner
- **Nieuw**: `.mq-devengine/workflow.yaml` per project -- Override van defaults

### YAML Schema

```yaml
name: standard
description: Full implementation workflow with deterministic validation
version: 1

defaults:
  model: sonnet
  timeout: 900          # 15 min per stap
  fresh_session: true   # Elke stap krijgt een schone context

steps:
  - name: explore
    type: prompt
    model: haiku
    command: explore_codebase
    timeout: 300
    description: "Verken de codebase en begrijp bestaande patronen"

  - name: plan
    type: prompt
    model: sonnet
    command: plan_implementation
    description: "Maak implementatieplan op basis van verkenning"

  - name: implement
    type: prompt
    model: sonnet
    command: coding_prompt
    repeat: per_task                # herhaalt per story-planner task
    retry: 2                        # max 2 retries bij falen
    fresh_session: true             # elke task = schone context
    description: "Implementeer de code"

  - name: lint
    type: deterministic
    run: "npm run lint && npm run build"
    retry: 0
    on_fail: retry_previous
    description: "Lint en type-check"

  - name: mock_check
    type: deterministic
    run: "grep -r 'globalThis|devStore|mockDb|mockData|fakeData' src/ --include='*.ts' --include='*.js' --exclude-dir='__tests__' --exclude-dir='node_modules'"
    expect_exit: 1                  # grep exit 1 = geen matches = goed
    on_fail: retry_previous
    description: "Controleer op hardcoded mock data"

  - name: test
    type: deterministic
    run: "npm test"
    retry: 0
    on_fail: retry_previous
    description: "Draai tests"

  - name: server_restart
    type: deterministic
    run: "workflow/scripts/server_restart_test.sh"
    retry: 0
    on_fail: retry_previous
    description: "Test data-persistentie na server restart"

  - name: review
    type: prompt
    model: haiku
    command: self_review
    fresh_session: true
    description: "Self-review tegen acceptance criteria"
```

### Kernconcepten
- **`type: prompt`** -- LLM sessie via Claude Agent SDK. Krijgt gefocuste prompt (~30 regels).
- **`type: deterministic`** -- Subprocess uitgevoerd door orchestrator. Kan NIET overgeslagen worden.
- **`repeat: per_task`** -- Expandeert op basis van story-planner output.
- **`on_fail: retry_previous`** -- Bij falen van deterministische stap, stuur de vorige prompt-stap opnieuw.
- **`fresh_session: true`** -- Start een nieuwe Claude sessie (schone context).
- **`expect_exit`** -- Verwachte exit code voor deterministische nodes.

---

## Stap 2: Workflow Engine

**Doel**: Python engine die YAML workflows parsed en uitvoert.

### Bestanden
- **Nieuw**: `workflow/engine.py` -- WorkflowEngine class
- **Nieuw**: `workflow/runner.py` -- StepRunner (prompt of deterministic)
- **Nieuw**: `workflow/state.py` -- WorkflowState tracking
- **Wijzig**: `parallel_orchestrator.py` -- Per feature een WorkflowEngine i.p.v. een coding agent subprocess
- **Wijzig**: `client.py` -- Gefocuste prompts per stap
- **Wijzig**: `role_registry.py` -- Workflow-step roles

### WorkflowEngine interface

```python
class WorkflowEngine:
    def __init__(self, workflow_yaml: Path, feature: Feature, project_dir: Path):
        self.steps: list[WorkflowStep]
        self.state: WorkflowState
        self.current_step: int
    
    async def run(self) -> WorkflowResult:
        for step in self.steps:
            if step.repeat == "per_task":
                for task in self.feature.tasks:
                    result = await self.run_step(step, task_context=task)
            else:
                result = await self.run_step(step)
            
            if result.failed and step.on_fail == "retry_previous":
                # Ga terug naar vorige prompt-stap met foutmelding
                ...
        return WorkflowResult(success=True)
    
    async def run_step(self, step, task_context=None) -> StepResult:
        self.emit_step_update(step, status="running")
        if step.type == "prompt":
            result = await self.run_prompt_step(step, task_context)
        elif step.type == "deterministic":
            result = await self.run_deterministic_step(step)
        self.emit_step_update(step, status="done" if result.ok else "failed")
        return result
```

---

## Stap 3: Gefocuste Prompt Templates

**Doel**: Splits de mega coding_prompt op in kleine prompts per stap.

### Bestanden
- **Nieuw**: `.claude/templates/workflow/explore.template.md` (~30 regels)
- **Nieuw**: `.claude/templates/workflow/plan.template.md` (~40 regels)
- **Nieuw**: `.claude/templates/workflow/implement.template.md` (~50 regels)
- **Nieuw**: `.claude/templates/workflow/self_review.template.md` (~30 regels)
- **Bewaar**: `.claude/templates/coding_prompt.template.md` -- Fallback voor v1

### Template variabelen
- `{{ feature.name }}`, `{{ feature.description }}`, `{{ feature.steps }}`
- `{{ task.name }}`, `{{ task.description }}` (bij repeat: per_task)
- `{{ previous_step.output }}` (plan -> implement)
- `{{ architecture_memory }}` (via memory_recall)

---

## Stap 4: Story Planner Integratie

**Doel**: Story planner output stuurt de workflow-expansie.

### Wijzigingen
- **Wijzig**: `story_planner_prompt.template.md` -- Gestructureerdere output met complexiteit + testbare criteria
- **Wijzig**: `mcp_server/feature_mcp.py` -- Extra metadata in `feature_create_sub_features()`
- **Wijzig**: `api/database.py` -- FeatureTask model + `complexity_hint`, `suggested_model`

### Flow
```
Story planner output:
  Task 1: "DB session tabel" (complexity: low, model: haiku)
  Task 2: "Auth endpoint"    (complexity: high, model: sonnet)  
  Task 3: "JWT tokens"       (complexity: medium, model: sonnet)

Workflow engine expandeert implement-stap:
  implement[1] -> Task 1 (haiku)
  implement[2] -> Task 2 (sonnet)
  implement[3] -> Task 3 (sonnet)
```

---

## Stap 5: WebSocket Protocol Uitbreiding

**Doel**: Real-time workflow step updates naar de UI.

### Nieuw message type

```typescript
interface WSWorkflowStepUpdate {
  type: 'workflow_step_update'
  featureId: number
  step: {
    name: string
    index: number
    total: number
    status: 'pending' | 'running' | 'done' | 'failed' | 'retrying'
    duration_ms?: number
    taskName?: string
    taskIndex?: number
    taskTotal?: number
    error?: string
  }
  timestamp: string
}
```

### Bestanden
- **Wijzig**: `server/websocket.py` -- Emit `workflow_step_update`
- **Wijzig**: `ui/src/lib/types.ts` -- TypeScript types
- **Wijzig**: `ui/src/hooks/useWebSocket.ts` -- Handler

---

## Stap 6: UI -- Stepper + Accordeon

**Doel**: Goals-view als primaire interface voor agent progress.

### Bestanden
- **Nieuw**: `ui/src/components/WorkflowStepper.tsx` -- Compacte stepper voor AgentCard
- **Nieuw**: `ui/src/components/WorkflowAccordion.tsx` -- Uitklapbare accordeon
- **Nieuw**: `ui/src/components/WorkflowStepDetail.tsx` -- Tool-call detail per stap
- **Wijzig**: `ui/src/components/AgentCard.tsx` -- WorkflowStepper integreren
- **Wijzig**: `ui/src/components/FeatureModal.tsx` -- WorkflowAccordion als tab

### UI Mockups

AgentCard met stepper:
```
+-----------------------------+
| Spark  -  CODING            |
| Feature 1.2: Auth endpoint  |
| V-V->-o-o-o  stap 3/6      |
| "Implementing JWT..."       |
+-----------------------------+
```

Feature detail met accordeon:
```
Feature 1.2: Auth endpoint

v V Explore (2 min)
  +-- Read 3 files
  +-- Scanned auth patterns

v V Plan (3 min)
  +-- Created implementation approach

v > Implement -- Task 2/5: "Auth endpoint"
  +-- Edit auth_routes.py
  +-- Edit jwt_utils.py
  +-- ... (live updating)

> o Lint
> o Mock Check
> o Test
> o Server Restart
> o Review
```

### State management

```typescript
interface FeatureWorkflowState {
  featureId: number
  steps: Array<{
    name: string
    status: 'pending' | 'running' | 'done' | 'failed' | 'retrying'
    duration_ms?: number
    taskName?: string
    toolCalls?: AgentLogEntry[]
  }>
  currentStepIndex: number
}

// In useWebSocket state:
workflowStates: Map<featureId, FeatureWorkflowState>
```

---

## Stap 7: Planning Sync Afmaken

**Doel**: Bidirectionele mq-planning sync inclusief workflow-stap status.

### Bestanden
- **Wijzig**: `planning_sync/sync_service.py` -- Workflow step status syncen
- **Wijzig**: `planning_sync/completion.py` -- Afmaken
- **Wijzig**: `planning_sync/models.py` -- Afmaken
- **Afmaken**: `planning_sync/narrative_renderer.py`, `report_generator.py`
- **Evalueren**: `demo_capture.py`, `demo_seed.py`, `screenshot_validator.py`

---

## Stap 8: Deterministische Scripts

### Bestanden
- **Nieuw**: `workflow/scripts/mock_data_check.sh`
- **Nieuw**: `workflow/scripts/server_restart_test.sh`
- **Hergebruik**: Project-type detectie via `server/services/project_config.py`

### Script detectie per project-type
- Node.js: `npm run lint`, `npm test`
- Python: `ruff check .`, `pytest`
- Custom: uit `.mq-devengine/workflow.yaml`

---

## Stap 9: Backward Compatibility

- Projecten zonder `workflow.yaml` -> `workflow/defaults/standard.yaml`
- YOLO mode -> `workflow/defaults/yolo.yaml`
- Feature flag: `workflow_enabled` (default: true voor nieuwe projecten)
- `coding_prompt.template.md` blijft als fallback
- Bestaande MCP tools ongewijzigd

---

## Verificatie

### Tests
- `test_workflow_schema.py` -- YAML parsing/validatie
- `test_workflow_engine.py` -- Step executie, retry, per_task expansie
- `test_deterministic_steps.py` -- Mock check, lint, test subprocesses

### Handmatig
- Start DevEngine -> voer workflow uit -> verifieer alle stappen
- WebSocket messages per step transition
- UI stepper + accordeon
- Deterministic nodes NIET overslaanbaar
- Retry bij deterministic failure
- mq-planning sync van workflow status
- YOLO mode met yolo.yaml
- Project zonder story-planner

---

## Samenvatting wijzigingen

| Categorie | Nieuw | Gewijzigd |
|-----------|-------|-----------|
| Workflow engine | `workflow/schema.py`, `engine.py`, `runner.py`, `state.py` | `parallel_orchestrator.py`, `client.py`, `role_registry.py` |
| YAML configs | `workflow/defaults/standard.yaml`, `yolo.yaml`, `minimal.yaml` | -- |
| Prompt templates | `workflow/explore.template.md`, `plan.template.md`, `implement.template.md`, `self_review.template.md` | `story_planner_prompt.template.md` |
| Scripts | `workflow/scripts/mock_data_check.sh`, `server_restart_test.sh` | -- |
| Backend | -- | `server/websocket.py`, `api/database.py`, `mcp_server/feature_mcp.py` |
| Frontend | `WorkflowStepper.tsx`, `WorkflowAccordion.tsx`, `WorkflowStepDetail.tsx` | `AgentCard.tsx`, `FeatureModal.tsx`, `useWebSocket.ts`, `types.ts` |
| Planning sync | -- | `planning_sync/sync_service.py`, `completion.py`, `models.py`, `narrative_renderer.py`, `report_generator.py` |

---

## Beslissingen genomen

| Vraag | Beslissing | Reden |
|-------|-----------|-------|
| Workflow definitie | YAML (niet Python) | Declaratief, per-project configureerbaar, deelbaar, UI-renderbaar |
| UI visualisatie | Stepper + accordeon | Combineert compact overzicht met drill-down naar tool-calls |
| Deterministische nodes | Alles: lint + test + mock-check + server-restart | Volledige coverage, agent kan niets overslaan |
| v1 afsluiting | Merge alles naar master, tag v1.0.0 | Clean break |
| planning_sync | Meenemen in v2 | Workflow status syncen naar mq-planning |
| Story planner | Integreren als workflow-stap input | Output expandeert de implement-stap dynamisch |
