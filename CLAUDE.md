# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Sprint 1 Blok A — v1→v2 Story rename (2026-04-11)

De database tabel `features` is hernoemd naar `stories` als eerste stap van Sprint 1 (zie `mq-platform/docs/platform-v2-sprint-plan.md` §Sprint 1). Dit is Blok A (DB schema) — Blok B (Python class rename, API endpoints, TypeScript types, MCP tools) is nog open.

**Huidige staat:**
- DB tabel: `stories` (was `features`)
- Python class: **nog steeds** `Feature` — `__tablename__ = "stories"`. Class rename komt in Blok B (taken 1.5-1.8)
- Kolom `acceptance_criteria` bestaat. Kolom `steps` bestaat ook nog (legacy). Data uit `steps` is gemigreerd naar `acceptance_criteria` waar die NULL was.
- Kolom `tasks` bestond al nooit — task 1.3 is een gedocumenteerde no-op.
- Migratie function: `_migrate_rename_features_to_stories` in `api/database.py`, draait BEFORE `create_all` zodat v1 DBs upgraden en fresh DBs direct `stories` aanmaken.
- ForeignKeys in `test_runs.feature_id` en `agent_logs.feature_id` wijzen nu naar `stories.id`.

**Voor code die nog `feature` referenties heeft (Blok B scope):**
- `server/routers/features.py` — taak 1.5, endpoints `/features` → `/stories`
- `server/schemas.py` — taak 1.6, Pydantic types (`steps` field → `acceptance_criteria`)
- `mcp_server/feature_mcp.py` — taak 1.7, MCP tool names `feature_*` → `story_*`
- Prompt templates — taak 1.8

Importeer `Feature` zoals voorheen — de class naam wijzigt pas in Blok B.

## Sprint 1 Blok B — API + types rename (2026-04-11) — PARTIAL DONE

Na Blok A is Blok B begonnen met een pragmatische scope: het HTTP-oppervlak en client-URL's zijn gesynchroniseerd, type-aliases toegevoegd, MCP en prompts grotendeels open gelaten omdat ze risicovol zijn voor een haastig-grote pass.

**Task 1.5 — API endpoints /features → /stories: ✅ DONE**
- `server/routers/features.py` router prefix veranderd naar `/api/projects/{project_name}/stories`
- Tags veranderd naar `["stories"]`
- Bestandsnaam is nog steeds `features.py` (interne rename volgt in later pass)
- 12 endpoints werken nu alleen onder `/stories` — de legacy `/features` path is verdwenen

**Task 1.6 — TypeScript types Feature → Story: 🟡 PARTIAL**
- `ui/src/lib/api.ts`: 12 URL-strings gewijzigd van `/features` → `/stories` (matches server)
- `ui/src/lib/types.ts`: Story aliases toegevoegd onderaan: `export type Story = Feature`, `StoryStatus`, `StoryListResponse`, `StoryCreate`, `StoryUpdate`
- Componenten (`FeatureCard.tsx`, `KanbanBoard.tsx`, etc.) gebruiken nog `Feature` — incrementeel te migreren in vervolg-PR

**Task 1.7 — MCP tools feature_* → story_*: 🟡 DEFERRED**
- `mcp_server/feature_mcp.py` docstring bijgewerkt met Blok B status-notitie
- 25 tool-decoratoren zijn nog `@mcp.tool()` met `feature_*` functienaam
- Rename naar `story_*` aliases (backward compat) volgt in een separate pass — te risicovol voor massa-rename in één commit
- Externe code die deze tools aanroept blijft werken zonder wijziging

**Task 1.8 — Prompt templates "feature" → "user story": 🟡 MINIMAL**
- `.claude/templates/architect_prompt.template.md`: 1 ref bijgewerkt
- Andere templates hebben nog veel refs (coding: 33, initializer: 13, review: 23, testing: 25)
- Vervolg-pass nodig voor volledige sprint-terminologie

**Overall Blok B status:** API surface en UI klant-URLs zijn consistent (meest kritieke deel). MCP tools, Python-schemas en prompt templates zijn open — deze raken geen gebruikers-gezicht maar wel internal agent-communicatie.

### Blok B voltooiing (2026-04-11 — part 2)

Blok B is daarna verder afgemaakt:

**1.6 TypeScript types Story canonical:**
- `ui/src/lib/types.ts`: `Story` is nu de canonieke interface, `Feature` is `@deprecated` alias via `export type Feature = Story`
- Hetzelfde voor `StoryStatus/FeatureStatus`, `StoryListResponse/FeatureListResponse`, `StoryCreate/FeatureCreate`, `StoryUpdate/FeatureUpdate`
- Bestaande componenten die `Feature` importeren blijven werken dankzij de alias
- Incrementeel migreren van componenten naar `Story` types kan in vervolg zonder functionele impact

**1.7 MCP tool aliases (22 tools):**
- In `mcp_server/feature_mcp.py` aan het einde: voor elk van de 22 `feature_*` tools is een `story_*` alias geregistreerd via `mcp.tool(name="story_xxx")(feature_xxx)`
- FastMCP `tool(name=...)` parameter maakt dit mogelijk zonder wrapper-functies
- Het bestand heeft nu 47 MCP tools totaal (22 feature_ + 22 story_ + 3 memory tools)
- 13 raw `UPDATE features` SQL statements bijgewerkt naar `UPDATE stories` (waren stale referenties naar pre-Blok-A state)

**1.8 Prompt templates (5 files):**
- `.claude/templates/coding_prompt.template.md`: 0 narrative feature refs
- `.claude/templates/initializer_prompt.template.md`: 0 refs
- `.claude/templates/review_prompt.template.md`: 0 refs
- `.claude/templates/testing_prompt.template.md`: 0 refs
- `.claude/templates/architect_prompt.template.md`: 0 refs
- Tool name verwijzingen (`feature_get_by_id` etc.) bleven intact — die werken via de story_* aliases maar klantprompts gebruiken nog canonieke namen voor backward compat

## Sprint 1 Blok C — Codex review integratie (2026-04-11) — INITIAL DONE

Nieuwe module `api/codex_review.py` geïntroduceerd als onafhankelijke code reviewer via OpenAI Codex CLI. Feature-flagged via `CODEX_REVIEW_ENABLED` env var.

**Waarom Codex:** de bestaande Claude-based review agent reviewt Claude-gegenereerde code. Dat is geen onafhankelijke review. Codex (gpt-5-codex / gpt-5) is een ander systeem en kan bias-blind-spots doorbreken.

**Task 1.9 Codex invocation:** ✅ `codex_review_story()` runt `codex exec --skip-git-repo-check -m gpt-5-codex --sandbox read-only` als subprocess. Prompt wordt via stdin verstuurd. Timeout 300s. Stdout wordt geparseerd voor een `VERDICT: APPROVED` of `VERDICT: REJECTED` marker.

**Task 1.10 Prompt assembly:** ✅ `build_review_prompt()` bouwt de review-prompt met:
- Story-header (ID, naam, beschrijving)
- Acceptance criteria lijst
- Tech stack context (optioneel)
- Definition of Done checklist (default 9 items, override-baar)
- De diff (git diff of file contents)
- Expliciete verdict-format eis (laatste regel `VERDICT: APPROVED|REJECTED`)

**Task 1.11 Retry flow:** ✅ `review_with_retry()` runt review loop:
- Attempt 1: review. Approved → return. Rejected → continue.
- `on_retry` hook aangeroepen na elke reject zodat caller een coding-agent retry kan triggeren
- `diff_fn` callback wordt bij elke attempt aangeroepen voor een *verse* diff (na coding agent fix)
- Error status krijgt één transient retry, daarna escalate
- Na max_retries (default 3) rejected verdicts → status = `escalate` (handmatige escalatie)

**Smoke tests uitgevoerd:**
- Real Codex call tegen een trivial story: 6 seconden, `rejected` met redelijke uitleg (model=gpt-5-codex, reasoning=low)
- Retry flow tot escalation: max_retries=2 → escalate na 2 rejected verdicts, on_retry hook 1x aangeroepen tussendoor

**Nog te doen voor volledige Blok C:**
- Integratie in `parallel_orchestrator.py` `_maintain_review_agents`: feature-flag check → Codex of legacy Claude reviewer — ✅ **DONE 2026-04-11**
- Persistence van Codex review results in `review_status` + `review_notes` kolommen van stories tabel — ✅ **DONE 2026-04-11**
- Mechanisme voor coding agent om reject notes als context te krijgen voor retry (koppeling `on_retry` hook aan coding agent spawn) — deferred (loopt via existing pending_review state machine)
- Unit tests in `tests/test_codex_review.py` — deferred

### Blok C voltooiing — Orchestrator integratie (2026-04-11)

Codex review is nu volledig geïntegreerd in de parallel orchestrator als alternatief voor de Claude-based review agent. Feature-flagged via `DEVENGINE_CODEX_REVIEW_ENABLED` env var — default **off**, dus bestaande gedrag ongewijzigd.

**Nieuwe orchestrator-state:**
- `self.running_codex_reviews: dict[int, tuple[Thread, datetime]]` — tracked naast `running_review_agents`. Keyed by feature_id omdat het threads zijn, geen subprocesses.

**Nieuwe orchestrator-methods** (in `parallel_orchestrator.py`):
- `_is_codex_review_enabled()` — delegeert naar `api.codex_review.is_codex_review_enabled()` (env var check)
- `_get_review_diff()` — fetcht de diff voor review: probeert eerst `git diff HEAD` (uncommitted changes van de coding agent), anders `git show HEAD` (laatste commit). Geeft een placeholder terug als er niets is.
- `_update_review_status_in_db(feature_id, status, notes)` — persist het Codex verdict: mapt `approved/rejected/escalate/error` naar `review_status` kolom, truncated `notes` naar 5000 chars. Op `approved` zet ook `feature.passes=True` en clear `in_progress`.
- `_run_codex_review_sync(feature_id)` — thread body: fetcht story + diff → roept `review_with_retry` aan → persist verdict → removes self from tracking dict → signals completion
- `_spawn_codex_review(feature_id)` — start een daemon thread, tracked in `running_codex_reviews`. Respecteert `MAX_TOTAL_AGENTS` limiet.

**Wijzigingen in bestaande methods:**
- `_get_pending_review_features()` — excludeert nu ook features die momenteel door Codex threads gereviewd worden
- `_maintain_review_agents()` — checkt feature flag: als Codex → `_spawn_codex_review`, anders bestaande `_spawn_review_agent` (Claude subprocess)
- `stop_agents()` — cleared `running_codex_reviews` bij shutdown (threads zijn daemon en sterven mee)
- `get_status()` — exposes `codex_review_count` naast `review_agent_count`

**Flow bij `DEVENGINE_CODEX_REVIEW_ENABLED=true`:**
1. Coding agent markt story als `pending_review` via `feature_mark_for_review`
2. Main orchestrator loop roept `_maintain_review_agents` aan
3. Flag is on → `_spawn_codex_review(feature_id)` start daemon thread
4. Thread fetcht story data + git diff, roept `codex_review.review_with_retry` aan (max_retries=1 voor orchestrator context)
5. Codex subprocess draait 6-30 sec afhankelijk van reasoning effort
6. Verdict → `_update_review_status_in_db` → review_status gezet, bij approved: passes=True
7. Thread removes zichzelf uit `running_codex_reviews`, signals completion

**Gedeferd voor latere pass:**
- Coding agent auto-retry op rejected: momenteel blijft een rejected story op `review_status=rejected` staan. Een vervolgstap kan een trigger toevoegen die rejected stories opnieuw als coding task in de queue plaatst met de reject notes als context in de prompt.
- Unit tests voor de nieuwe orchestrator methods en end-to-end Codex flow.

**Verificatie import chain:**
```
✓ parallel_orchestrator importeert
  - 5 nieuwe methods aanwezig: _is_codex_review_enabled, _get_review_diff,
    _update_review_status_in_db, _run_codex_review_sync, _spawn_codex_review
  - running_codex_reviews dict op __init__
  - get_status exposes codex_review_count
✓ api.codex_review, api.git_commit, api.dependency_resolver all clean
✓ Feature.__tablename__ = stories (Blok A preserved)
✓ Feature flags default off: is_codex_review_enabled=False, is_git_commit_enabled=False
```

**Gebruik (handmatig, vóór orchestrator integratie):**
```python
from api.codex_review import review_with_retry
from pathlib import Path

verdict = review_with_retry(
    story_id=42,
    story_name="Add user login",
    story_description="...",
    acceptance_criteria=["AC1: ...", "AC2: ..."],
    diff_fn=lambda: subprocess.run(["git","diff","HEAD~1"], capture_output=True, text=True).stdout,
    project_dir=Path("/path/to/project"),
    tech_stack="FastAPI + PostgreSQL",
    max_retries=3,
)
# verdict.status in {"approved", "escalate", "error"}
```

## Sprint 1 Blok D — Traceability + sizing hints (2026-04-11) — DONE

**Task 1.12 Git commit per story: ✅ DONE**
- Nieuwe module `api/git_commit.py`:
  - `build_commit_message(story_id, name, desc, acs)` — deterministic format: `story #{id}: {name}` + body + AC list + source marker
  - `commit_story(project_dir, ...)` — runt `git add -A && git commit` met subprocess, returned `CommitResult` met hash/files/errors
  - `commit_story_if_enabled(...)` — feature-flagged wrapper (env `DEVENGINE_GIT_COMMIT_ENABLED=true`, default off)
- Integratie in `parallel_orchestrator.py._on_agent_complete`: na session.expire_all() worden alle stories die `passes=True` zijn geworden opgeslagen in een lijst; na session.close() wordt `commit_story_if_enabled` per story aangeroepen (buiten de DB sessie om blocking te vermijden)
- Feature flag is standaard **UIT** zodat bestaande gedrag ongewijzigd blijft
- Getest met real git temp repo: `story #42: Add login endpoint` commit met correcte hash en message

**Task 1.13 Story planner sizing hints: ✅ DONE**
- Uitgebreid in `api/dependency_resolver.py`:
  - `StorySizingHint` TypedDict: scope / context_radius / context_budget_pct / complexity_score / reasons
  - `estimate_story_size(story) -> StorySizingHint` — heuristiek op basis van description length, AC count, dependencies, category
  - Scope mapping via threshold-tabel: small (≤20), medium (≤50), large (≤80), extra_large (>80)
  - Explicit override via `story["scope"]` of `story["context_radius"]`
  - `annotate_stories_with_sizing(stories)` — returns stories met `_sizing_hint` field
- `get_ready_features` bijgewerkt: tiebreaker op complexity_score (kleinere stories eerst bij gelijke scheduling score)
- Context budget estimate (% van agent context nodig) gekoppeld aan scope voor toekomstige budget-aware scheduling
- Getest: trivial story → small/complexity=15; architecture+4deps+8ACs → extra_large/complexity=97

**Sprint 1 voortgang na Blok D: 15 van 16 taken DONE (94%).**
Alleen Blok E (cleanup + UI — taken 1.14-1.16) resterend.

## Prerequisites

- Python 3.11+
- Node.js 20+ (for UI development)
- Claude Code CLI

## Project Overview

This is an autonomous coding agent system with a React-based UI. It uses the Claude Agent SDK to build complete applications over multiple sessions using a two-agent pattern:

1. **Initializer Agent** - First session reads an app spec and creates features in a SQLite database
2. **Coding Agent** - Subsequent sessions implement features one by one, marking them as passing

## Commands

### npm Global Install (Recommended)

```bash
npm install -g mq-devengine-ai
mq-devengine                    # Start server (first run sets up Python venv)
mq-devengine config             # Edit ~/.mq-devengine/.env in $EDITOR
mq-devengine config --show      # Print active configuration
mq-devengine --port 9999        # Custom port
mq-devengine --no-browser       # Don't auto-open browser
mq-devengine --repair           # Delete and recreate ~/.mq-devengine/venv/
```

### From Source (Development)

```bash
# Launch Web UI (serves pre-built React app)
start_ui.bat      # Windows
./start_ui.sh     # macOS/Linux

# CLI menu
start.bat         # Windows
./start.sh        # macOS/Linux
```

### Python Backend (Manual)

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the main CLI launcher
python start.py

# Run agent directly for a project (use absolute path or registered name)
python autonomous_agent_demo.py --project-dir C:/Projects/my-app
python autonomous_agent_demo.py --project-dir my-app  # if registered

# YOLO mode: rapid prototyping without browser testing
python autonomous_agent_demo.py --project-dir my-app --yolo

# Parallel mode: run multiple agents concurrently (1-5 agents)
python autonomous_agent_demo.py --project-dir my-app --parallel --max-concurrency 3

# Batch mode: implement multiple features per agent session (1-3)
python autonomous_agent_demo.py --project-dir my-app --batch-size 3

# Batch specific features by ID
python autonomous_agent_demo.py --project-dir my-app --batch-features 1,2,3
```

### YOLO Mode (Rapid Prototyping)

YOLO mode skips all testing for faster feature iteration:

```bash
# CLI
python autonomous_agent_demo.py --project-dir my-app --yolo

# UI: Toggle the lightning bolt button before starting the agent
```

**What's different in YOLO mode:**
- No regression testing
- No Playwright MCP server (browser automation disabled)
- Features marked passing after lint/type-check succeeds
- Faster iteration for prototyping

**What's the same:**
- Lint and type-check still run to verify code compiles
- Feature MCP server for tracking progress
- All other development tools available

**When to use:** Early prototyping when you want to quickly scaffold features without verification overhead. Switch back to standard mode for production-quality development.

### React UI (in ui/ directory)

```bash
cd ui
npm install
npm run dev      # Development server (hot reload)
npm run build    # Production build (required for start_ui.bat)
npm run lint     # Run ESLint
```

**Note:** The `start_ui.bat` script serves the pre-built UI from `ui/dist/`. After making UI changes, run `npm run build` in the `ui/` directory.

## Testing

### Python

```bash
ruff check .                          # Lint
mypy .                                # Type check
python test_security.py               # Security unit tests (12 tests)
python test_security_integration.py   # Integration tests (9 tests)
python -m pytest test_client.py       # Client tests (20 tests)
python -m pytest test_dependency_resolver.py  # Dependency resolver tests (12 tests)
python -m pytest test_rate_limit_utils.py     # Rate limit tests (22 tests)
```

### React UI

```bash
cd ui
npm run lint          # ESLint
npm run build         # Type check + build (Vite 7)
npm run test:e2e      # Playwright end-to-end tests
npm run test:e2e:ui   # Playwright tests with UI
```

### CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to master:
- **Python job**: ruff lint + security tests
- **UI job**: ESLint + TypeScript build

### Code Quality

Configuration in `pyproject.toml`:
- ruff: Line length 120, Python 3.11 target
- mypy: Strict return type checking, ignores missing imports

## Architecture

### npm CLI (bin/, lib/)

The `mq-devengine` command is a Node.js wrapper that manages the Python environment and server lifecycle:
- `bin/mq-devengine.js` - Entry point (shebang script)
- `lib/cli.js` - Main CLI logic: Python 3.11+ detection (cross-platform), venv management at `~/.mq-devengine/venv/` with composite marker (requirements hash + Python version), `.env` config loading from `~/.mq-devengine/.env`, uvicorn server startup with PID file, and signal handling
- `package.json` - npm package config (`mq-devengine-ai` on npm), `files` whitelist with `__pycache__` exclusions, `prepublishOnly` builds the UI
- `requirements-prod.txt` - Runtime-only Python deps (excludes ruff, mypy, pytest)
- `.npmignore` - Excludes dev files, tests, UI source from the published tarball

Publishing: `npm publish` (triggers `prepublishOnly` which builds UI, then publishes ~600KB tarball with 84 files)

### Core Python Modules

- `start.py` - CLI launcher with project creation/selection menu
- `autonomous_agent_demo.py` - Entry point for running the agent (supports `--yolo`, `--parallel`, `--batch-size`, `--batch-features`)
- `devengine_paths.py` - Central path resolution with dual-path backward compatibility and migration
- `agent.py` - Agent session loop using Claude Agent SDK
- `client.py` - ClaudeSDKClient configuration with security hooks, MCP servers, and Vertex AI support
- `security.py` - Bash command allowlist validation (ALLOWED_COMMANDS whitelist)
- `prompts.py` - Prompt template loading with project-specific fallback and batch feature prompts
- `progress.py` - Progress tracking, database queries, webhook notifications
- `registry.py` - Project registry for mapping names to paths (cross-platform), global settings model
- `parallel_orchestrator.py` - Concurrent agent execution with dependency-aware scheduling
- `auth.py` - Authentication error detection for Claude CLI
- `env_constants.py` - Shared environment variable constants (API_ENV_VARS) used by client.py and chat sessions
- `rate_limit_utils.py` - Rate limit detection, retry parsing, exponential backoff with jitter
- `api/database.py` - SQLAlchemy models (Feature, Schedule, ScheduleOverride)
- `api/dependency_resolver.py` - Cycle detection (Kahn's algorithm + DFS) and dependency validation
- `api/migration.py` - JSON-to-SQLite migration utility

### Project Registry

Projects can be stored in any directory. The registry maps project names to paths using SQLite:
- **All platforms**: `~/.mq-devengine/registry.db`

The registry uses:
- SQLite database with SQLAlchemy ORM
- POSIX path format (forward slashes) for cross-platform compatibility
- SQLite's built-in transaction handling for concurrency safety

### Server API (server/)

The FastAPI server provides REST and WebSocket endpoints for the UI:

**Routers** (`server/routers/`):
- `projects.py` - Project CRUD with registry integration
- `features.py` - Feature management
- `agent.py` - Agent control (start/stop/pause/resume)
- `filesystem.py` - Filesystem browser API with security controls
- `spec_creation.py` - WebSocket for interactive spec creation
- `expand_project.py` - Interactive project expansion via natural language
- `assistant_chat.py` - Read-only project assistant chat (WebSocket/REST)
- `terminal.py` - Interactive terminal I/O with PTY support (WebSocket bidirectional)
- `devserver.py` - Dev server control (start/stop) and config
- `schedules.py` - CRUD for time-based agent scheduling
- `settings.py` - Global settings management (model selection, YOLO, batch size, headless browser)

**Services** (`server/services/`):
- `process_manager.py` - Agent process lifecycle management
- `project_config.py` - Project type detection and dev command management
- `terminal_manager.py` - Terminal session management with PTY (`pywinpty` on Windows)
- `scheduler_service.py` - APScheduler-based automated agent scheduling
- `dev_server_manager.py` - Dev server lifecycle management
- `assistant_chat_session.py` / `assistant_database.py` - Assistant chat sessions with SQLite persistence
- `spec_chat_session.py` - Spec creation chat sessions
- `expand_chat_session.py` - Expand project chat sessions
- `chat_constants.py` - Shared constants for chat services

**Utilities** (`server/utils/`):
- `process_utils.py` - Process management utilities
- `project_helpers.py` - Project path resolution helpers
- `validation.py` - Project name validation

### Feature Management

Features are stored in SQLite (`features.db`) via SQLAlchemy. The agent interacts with features through an MCP server:

- `mcp_server/feature_mcp.py` - MCP server exposing feature management tools
- `api/database.py` - SQLAlchemy models (Feature table with priority, category, name, description, steps, passes, dependencies)

MCP tools available to the agent:
- `feature_get_stats` - Progress statistics
- `feature_get_by_id` - Get a single feature by ID
- `feature_get_summary` - Get summary of all features
- `feature_get_ready` - Get features ready to work on (dependencies met)
- `feature_get_blocked` - Get features blocked by unmet dependencies
- `feature_get_graph` - Get full dependency graph
- `feature_claim_and_get` - Atomically claim next available feature (for parallel mode)
- `feature_mark_in_progress` - Mark feature as in progress
- `feature_mark_passing` - Mark feature complete
- `feature_mark_failing` - Mark feature as failing
- `feature_skip` - Move feature to end of queue
- `feature_clear_in_progress` - Clear in-progress status
- `feature_create_bulk` - Initialize all features (used by initializer)
- `feature_create` - Create a single feature
- `feature_add_dependency` - Add dependency between features (with cycle detection)
- `feature_remove_dependency` - Remove a dependency
- `feature_set_dependencies` - Set all dependencies for a feature at once

### React UI (ui/)

- Tech stack: React 19, TypeScript, Vite 7, TanStack Query, Tailwind CSS v4, Radix UI, dagre (graph layout), xterm.js (terminal)
- `src/App.tsx` - Main app with project selection, kanban board, agent controls
- `src/hooks/useWebSocket.ts` - Real-time updates via WebSocket (progress, agent status, logs, agent updates)
- `src/hooks/useProjects.ts` - React Query hooks for API calls
- `src/lib/api.ts` - REST API client
- `src/lib/types.ts` - TypeScript type definitions

Key components:
- `AgentMissionControl.tsx` - Dashboard showing active agents with mascots (Spark, Fizz, Octo, Hoot, Buzz)
- `DependencyGraph.tsx` - Interactive node graph visualization with dagre layout
- `CelebrationOverlay.tsx` - Confetti animation on feature completion
- `FolderBrowser.tsx` - Server-side filesystem browser for project folder selection
- `Terminal.tsx` / `TerminalTabs.tsx` - xterm.js-based multi-tab terminal
- `AssistantPanel.tsx` / `AssistantChat.tsx` - AI assistant for project Q&A
- `ExpandProjectModal.tsx` / `ExpandProjectChat.tsx` - Add features via natural language
- `DevServerControl.tsx` - Dev server start/stop control
- `ScheduleModal.tsx` - Schedule management UI
- `SettingsModal.tsx` - Global settings panel

In-app documentation (`/#/docs` route):
- `src/components/docs/sections/` - Content for each doc section (GettingStarted.tsx, AgentSystem.tsx, etc.)
- `src/components/docs/docsData.ts` - Sidebar structure, subsection IDs, search keywords
- `src/components/docs/DocsPage.tsx` - Page layout; `DocsContent.tsx` - section renderer with scroll tracking

Keyboard shortcuts (press `?` for help):
- `D` - Toggle debug panel
- `G` - Toggle Kanban/Graph view
- `N` - Add new feature
- `A` - Toggle AI assistant
- `,` - Open settings

### Project Structure for Generated Apps

Projects can be stored in any directory (registered in `~/.mq-devengine/registry.db`). Each project contains:
- `.mq-devengine/prompts/app_spec.txt` - Application specification (XML format)
- `.mq-devengine/prompts/initializer_prompt.md` - First session prompt
- `.mq-devengine/prompts/coding_prompt.md` - Continuation session prompt
- `.mq-devengine/features.db` - SQLite database with feature test cases
- `.mq-devengine/.agent.lock` - Lock file to prevent multiple agent instances
- `.mq-devengine/allowed_commands.yaml` - Project-specific bash command allowlist (optional)
- `.mq-devengine/.gitignore` - Ignores runtime files
- `CLAUDE.md` - Stays at project root (SDK convention)
- `app_spec.txt` - Root copy for agent template compatibility

Legacy projects with files at root level (e.g., `features.db`, `prompts/`) are auto-migrated to `.mq-devengine/` on next agent start. Dual-path resolution ensures old and new layouts work transparently.

### Security Model

Defense-in-depth approach configured in `client.py`:
1. OS-level sandbox for bash commands
2. Filesystem restricted to project directory only
3. Bash commands validated using hierarchical allowlist system

#### Extra Read Paths (Cross-Project File Access)

The agent can optionally read files from directories outside the project folder via the `EXTRA_READ_PATHS` environment variable. This enables referencing documentation, shared libraries, or other projects.

**Configuration:**

```bash
# Single path
EXTRA_READ_PATHS=/Users/me/docs

# Multiple paths (comma-separated)
EXTRA_READ_PATHS=/Users/me/docs,/opt/shared-libs,/Volumes/Data/reference
```

**Security Controls:**

All paths are validated before being granted read access:
- Must be absolute paths (not relative)
- Must exist and be directories
- Paths are canonicalized via `Path.resolve()` to prevent `..` traversal attacks
- Sensitive directories are blocked (see blocklist below)
- Only Read, Glob, and Grep operations are allowed (no Write/Edit)

**Blocked Sensitive Directories:**

The following directories (relative to home) are always blocked:
- `.ssh`, `.aws`, `.azure`, `.kube` - Cloud/SSH credentials
- `.gnupg`, `.gpg`, `.password-store` - Encryption keys
- `.docker`, `.config/gcloud` - Container/cloud configs
- `.npmrc`, `.pypirc`, `.netrc` - Package manager credentials

#### Per-Project Allowed Commands

The agent's bash command access is controlled through a hierarchical configuration system:

**Command Hierarchy (highest to lowest priority):**
1. **Hardcoded Blocklist** (`security.py`) - NEVER allowed (dd, sudo, shutdown, etc.)
2. **Org Blocklist** (`~/.mq-devengine/config.yaml`) - Cannot be overridden by projects
3. **Org Allowlist** (`~/.mq-devengine/config.yaml`) - Available to all projects
4. **Global Allowlist** (`security.py`) - Default commands (npm, git, curl, etc.)
5. **Project Allowlist** (`.mq-devengine/allowed_commands.yaml`) - Project-specific commands

**Project Configuration:**

Each project can define custom allowed commands in `.mq-devengine/allowed_commands.yaml`:

```yaml
version: 1
commands:
  # Exact command names
  - name: swift
    description: Swift compiler

  # Prefix wildcards (matches swiftc, swiftlint, swiftformat)
  - name: swift*
    description: All Swift development tools

  # Local project scripts
  - name: ./scripts/build.sh
    description: Project build script
```

**Organization Configuration:**

System administrators can set org-wide policies in `~/.mq-devengine/config.yaml`:

```yaml
version: 1

# Commands available to ALL projects
allowed_commands:
  - name: jq
    description: JSON processor

# Commands blocked across ALL projects (cannot be overridden)
blocked_commands:
  - aws        # Prevent accidental cloud operations
  - kubectl    # Block production deployments
```

**Pattern Matching:**
- Exact: `swift` matches only `swift`
- Wildcard: `swift*` matches `swift`, `swiftc`, `swiftlint`, etc.
- Scripts: `./scripts/build.sh` matches the script by name from any directory

**Limits:**
- Maximum 100 commands per project config
- Blocklisted commands (sudo, dd, shutdown, etc.) can NEVER be allowed
- Org-level blocked commands cannot be overridden by project configs

**Files:**
- `security.py` - Command validation logic and hardcoded blocklist
- `test_security.py` - Unit tests for security system
- `test_security_integration.py` - Integration tests with real hooks
- `examples/project_allowed_commands.yaml` - Project config example (all commented by default)
- `examples/org_config.yaml` - Org config example (all commented by default)
- `examples/README.md` - Comprehensive guide with use cases, testing, and troubleshooting

### Vertex AI Configuration (Optional)

Run coding agents via Google Cloud Vertex AI:

1. Install and authenticate gcloud CLI: `gcloud auth application-default login`
2. Configure `.env`:
   ```
   CLAUDE_CODE_USE_VERTEX=1
   CLOUD_ML_REGION=us-east5
   ANTHROPIC_VERTEX_PROJECT_ID=your-gcp-project-id
   ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-5@20251101
   ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-5@20250929
   ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-3-5-haiku@20241022
   ```

**Note:** Use `@` instead of `-` in model names for Vertex AI.

### Ollama Local Models (Optional)

Run coding agents using local models via Ollama v0.14.0+:

1. Install Ollama: https://ollama.com
2. Start Ollama: `ollama serve`
3. Pull a coding model: `ollama pull qwen3-coder`
4. Configure `.env`:
   ```
   ANTHROPIC_BASE_URL=http://localhost:11434
   ANTHROPIC_AUTH_TOKEN=ollama
   API_TIMEOUT_MS=3000000
   ANTHROPIC_DEFAULT_SONNET_MODEL=qwen3-coder
   ANTHROPIC_DEFAULT_OPUS_MODEL=qwen3-coder
   ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen3-coder
   ```
5. Run MQ DevEngine normally - it will use your local Ollama models

**Recommended coding models:**
- `qwen3-coder` - Good balance of speed and capability
- `deepseek-coder-v2` - Strong coding performance
- `codellama` - Meta's code-focused model

**Model tier mapping:**
- Use the same model for all tiers, or map different models per capability level
- Larger models (70B+) work best for Opus tier
- Smaller models (7B-20B) work well for Haiku tier

**Known limitations:**
- Smaller context windows than Claude (model-dependent)
- Extended context beta disabled (not supported by Ollama)
- Performance depends on local hardware (GPU recommended)

## Claude Code Integration

**Slash commands** (`.claude/commands/`):
- `/create-spec` - Interactive spec creation for new projects
- `/expand-project` - Expand existing project with new features
- `/gsd-to-devengine-spec` - Convert GSD codebase mapping to app_spec.txt
- `/check-code` - Run lint and type-check for code quality
- `/checkpoint` - Create comprehensive checkpoint commit
- `/review-pr` - Review pull requests

**Custom agents** (`.claude/agents/`):
- `coder.md` - Elite software architect agent for code implementation (Opus)
- `code-review.md` - Code review agent for quality/security/performance analysis (Opus)
- `deep-dive.md` - Technical investigator for deep analysis and debugging (Opus)

**Skills** (`.claude/skills/`):
- `frontend-design` - Distinctive, production-grade UI design
- `gsd-to-devengine-spec` - Convert GSD codebase mapping to MQ DevEngine app_spec format

**Other:**
- `.claude/templates/` - Prompt templates copied to new projects
- `examples/` - Configuration examples and documentation for security settings

## Key Patterns

### Prompt Loading Fallback Chain

1. Project-specific: `{project_dir}/.mq-devengine/prompts/{name}.md` (or legacy `{project_dir}/prompts/{name}.md`)
2. Base template: `.claude/templates/{name}.template.md`

### Agent Session Flow

1. Check if `.mq-devengine/features.db` has features (determines initializer vs coding agent)
2. Create ClaudeSDKClient with security settings
3. Send prompt and stream response
4. Auto-continue with 3-second delay between sessions

### Real-time UI Updates

The UI receives updates via WebSocket (`/ws/projects/{project_name}`):
- `progress` - Test pass counts (passing, in_progress, total)
- `agent_status` - Running/paused/stopped/crashed
- `log` - Agent output lines with optional featureId/agentIndex for attribution
- `feature_update` - Feature status changes
- `agent_update` - Multi-agent state updates (thinking/working/testing/success/error) with mascot names

### Parallel Mode

When running with `--parallel`, the orchestrator:
1. Spawns multiple Claude agents as subprocesses (up to `--max-concurrency`)
2. Each agent claims features atomically via `feature_claim_and_get`
3. Features blocked by unmet dependencies are skipped
4. Browser contexts are isolated per agent using `--isolated` flag
5. AgentTracker parses output and emits `agent_update` messages for UI

### Process Limits (Parallel Mode)

The orchestrator enforces strict bounds on concurrent processes:
- `MAX_PARALLEL_AGENTS = 5` - Maximum concurrent coding agents
- `MAX_TOTAL_AGENTS = 10` - Hard limit on total agents (coding + testing)
- Testing agents are capped at `max_concurrency` (same as coding agents)
- Total process count never exceeds 11 Python processes (1 orchestrator + 5 coding + 5 testing)

### Multi-Feature Batching

Agents can implement multiple features per session using `--batch-size` (1-3, default: 3):
- `--batch-size N` - Max features per coding agent batch
- `--testing-batch-size N` - Features per testing batch (1-5, default: 3)
- `--batch-features 1,2,3` - Specific feature IDs for batch implementation
- `--testing-batch-features 1,2,3` - Specific feature IDs for batch regression testing
- `prompts.py` provides `get_batch_feature_prompt()` for multi-feature prompt generation
- Configurable in UI via settings panel

### Design System

The UI uses a **neobrutalism** design with Tailwind CSS v4:
- CSS variables defined in `ui/src/styles/globals.css` via `@theme` directive
- Custom animations: `animate-slide-in`, `animate-pulse-neo`, `animate-shimmer`
- Color tokens: `--color-neo-pending` (yellow), `--color-neo-progress` (cyan), `--color-neo-done` (green)
