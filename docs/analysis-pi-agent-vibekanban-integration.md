# Analyse: Pi Agent, Vibe Kanban & MQ DevEngine Integratie

**Datum:** 2026-02-28
**Status:** Research Complete - Actionable
**Context:** Onderzoek naar Pi Agent (Armin Ronacher) en Vibe Kanban (BloopAI) als mogelijke integratie/inspiratiebronnen voor MQ DevEngine.

---

## 1. Pi Agent: Architectuur & Bevindingen

### 1.1 Overzicht

Pi Agent is een minimalistisch coding agent framework van Armin Ronacher (bekend van Flask, Rye, UV).
Broncode: `badlogic/pi-mono` (TypeScript monorepo).

**Kernfilosofie:** "4 tools zijn genoeg" - Read, Write, Edit, Bash. Alles wat een agent nodig heeft om code te schrijven kan met deze 4 operaties. De rest is complexiteit die afleidt.

**Monorepo structuur:**
| Package | Functie |
|---------|---------|
| `pi-ai` | LLM abstractie (20+ providers, OAuth, custom models) |
| `pi-agent-core` | State machine, session management, tool execution |
| `pi-coding-agent` | Volledige agent: terminal, extensions, MCP |
| `pi-desktop` | Tauri desktop wrapper |

### 1.2 Vier Run Modes

Pi Agent ondersteunt 4 modi waarmee het embedded kan worden:

| Mode | Input/Output | Use Case |
|------|-------------|----------|
| **Interactive** | Terminal stdin/stdout | Ontwikkelaar in terminal |
| **Print** | Query in, tekst uit | Scripting, piping |
| **RPC** | JSON over stdin/stdout | **Headless embedding** |
| **SDK** | In-process TypeScript API | Native integratie |

### 1.3 SDK API

```typescript
import { createAgentSession } from "@mariozechner/pi-coding-agent";

const session = createAgentSession({
  model: { provider: "anthropic", model: "claude-sonnet-4-20250514" },
  tools: ["read", "write", "edit", "bash"],
  sessionManager: new FileSessionManager("./sessions"),
  resourceLoader: new LocalResourceLoader(),
});

// Prompt sturen
await session.prompt("Implementeer feature X");

// Events subscriben (streaming)
session.subscribe((event) => {
  if (event.type === "text") console.log(event.content);
  if (event.type === "tool_use") console.log(event.tool, event.input);
});

// Bijsturen (guidance injection)
await session.steer("Focus op de API eerst, UI later");

// Follow-up na voltooiing
await session.followUp("Voeg nu tests toe");
```

### 1.4 Session Trees (Context Management)

Pi gebruikt JSONL-bestanden met een boomstructuur (`id`/`parentId`) voor gespreksbeheer:
- **In-place branching**: vanuit elk punt een nieuw pad starten
- **Auto-compaction**: wanneer context vol raakt, vat een LLM de geschiedenis samen
- **Persistentie**: alle sessies bewaard als bestanden, hervat waar je was

### 1.5 Extension System

TypeScript modules geladen via `jiti` (JIT TypeScript compiler):
- Hot-reloadable zonder herstart
- Registreren: tools, commands, shortcuts, providers
- Community extensions mogelijk via npm packages

### 1.6 Pluggable Operations

De 4 tools (Read, Write, Edit, Bash) zijn geimplementeerd als **pluggable operations**:
- `BashOperations` - kan lokaal of remote draaien
- `ReadOperations` - filesystem abstractie
- Dit maakt remote execution mogelijk (agent draait lokaal, operaties op server)

---

## 2. Headless Operatie: Bewijs via OpenClaw

### 2.1 De Kernbevinding

**Pi Agent kan headless worden aangestuurd door externe systemen.** Dit is niet theoretisch -- het wordt actief gebruikt in productie door OpenClaw.

### 2.2 OpenClaw's PiEmbeddedRunner

OpenClaw (een coding platform) embed Pi Agent direct als library:

```
Architectuur:
+------------------+     +-------------------+     +------------------+
| OpenClaw Backend | --> | PiEmbeddedRunner  | --> | Pi Agent Core    |
| (Orchestrator)   |     | (Adapter Layer)   |     | (State Machine)  |
+------------------+     +-------------------+     +------------------+
                                                          |
                                                    +-----+-----+
                                                    |     |     |
                                                   Read Write  Bash
                                                    |     |     |
                                                 [Target Codebase]
```

**Wat OpenClaw doet:**
1. Importeert `@mariozechner/pi-agent-core` als npm dependency
2. Wraps de session API in een `PiEmbeddedRunner` klasse
3. Start sessions programmatisch (geen terminal nodig)
4. Subscribed op events voor real-time voortgangsrapportage
5. Stuurt de agent bij via `steer()` en `followUp()`

### 2.3 Waarom Dit Relevant Is Voor MQ DevEngine

MQ DevEngine draait agents als **subprocessen** via de Claude Agent SDK. Het `agent_runtime.py` abstractielaag (AgentClient protocol) maakt het mogelijk om Pi Agent als alternatieve runtime in te pluggen:

```
Huidige situatie:
parallel_orchestrator.py → subprocess → python agent.py → ClaudeAgentRuntime → Claude SDK

Met Pi runtime (optie A - RPC):
parallel_orchestrator.py → subprocess → node pi-agent → RPC JSON protocol

Met Pi runtime (optie B - SDK wrapper):
parallel_orchestrator.py → subprocess → python agent.py → PiAgentRuntime → Pi SDK (via Node child_process)
```

**Het AgentClient protocol dat we net gebouwd hebben maakt dit mogelijk:**

```python
# agent_runtime.py - het enige bestand dat verandert

class PiAgentRuntime:
    """Pi Agent achter hetzelfde AgentClient protocol."""

    async def __aenter__(self):
        # Start Pi Agent in RPC mode
        self._process = await asyncio.create_subprocess_exec(
            "npx", "pi-agent", "--mode", "rpc",
            stdin=PIPE, stdout=PIPE
        )
        return self

    async def query(self, message):
        # Stuur JSON-RPC bericht
        await self._write_json({"method": "prompt", "params": {"text": message}})

    async def receive_response(self):
        # Stream JSON events van stdout
        async for line in self._process.stdout:
            event = json.loads(line)
            yield self._convert_to_internal_format(event)
```

### 2.4 Voordelen van Pi als Alternatieve Runtime

| Voordeel | Detail |
|----------|--------|
| **20+ LLM providers** | Anthropic, OpenAI, Google, Mistral, Groq, Together, local Ollama, etc. |
| **Goedkopere modellen** | Sonnet/Haiku via Pi, Opus via Claude SDK -- per taak kiezen |
| **Session trees** | Branching en compaction out-of-the-box |
| **Extensions** | Community tools zonder onze codebase te wijzigen |
| **Failover** | Als Claude API down is, switch naar OpenAI/Gemini |

### 2.5 Beperkingen en Risico's

| Risico | Mitigatie |
|--------|-----------|
| Pi is nog jong (v0.x) | Alleen voor coding agents, niet voor initializer/reviewer |
| TypeScript ↔ Python bridge | RPC mode elimineert taalbarriere |
| Geen MCP support (native) | Pi heeft eigen extension system; of MCP via stdin/stdout bridge |
| Security model verschilt | Onze security.py hooks werken op subprocess niveau |
| Session persistence format | Converteren tussen JSONL (Pi) en onze SQLite (DevEngine) |

---

## 3. Vibe Kanban: Architectuur & Vergelijking

### 3.1 Overzicht

Vibe Kanban (`BloopAI/vibe-kanban`) is een AI-powered project management tool.
Tech stack: **Rust backend (Axum)** + **React 18 frontend** + pnpm workspaces.

### 3.2 Agent Executors (9 stuks)

Vibe Kanban ondersteunt 9 verschillende coding agents:

| Agent | Integratie |
|-------|-----------|
| Claude Code | CLI subprocess |
| Codex (OpenAI) | CLI subprocess |
| Gemini CLI | CLI subprocess |
| Amp | CLI subprocess |
| Cursor | CLI subprocess |
| Copilot | CLI subprocess |
| Opencode | CLI subprocess |
| Qwen | CLI subprocess |
| Droid | CLI subprocess |

**Belangrijk inzicht:** Allemaal CLI subprocess-gebaseerd -- exact hetzelfde patroon als MQ DevEngine.

### 3.3 State Management

| Technologie | Gebruik |
|------------|---------|
| Zustand | Client-side state stores |
| TanStack Query | Server state / caching |
| TanStack DB | Client-side reactive database |
| Immer | Immutable state updates |
| JSON Patch (RFC 6902) | Real-time sync (WebSocket) |
| ElectricSQL | Offline-first sync |

### 3.4 UI Architectuur

- **154 componenten** in een gestructureerde directory
- Rich text editor: Lexical
- Code editor: CodeMirror 6
- Diff viewer: custom
- Design system: IBM Plex fonts, semantic CSS tokens, 12px base grid

### 3.5 Git Worktree Isolatie

Vibe Kanban isoleert elke agent-taak in een aparte git worktree:
```
project/
  .git/worktrees/
    task-123/    # Agent 1 werkt hier
    task-456/    # Agent 2 werkt hier
  main/          # Hoofd-worktree
```

### 3.6 MCP Task Server

Agents communiceren terug naar het kanban bord via een MCP server:
- Feature status updates
- Voortgangsrapportage
- Vergelijkbaar met onze `feature_mcp.py`

---

## 4. Vergelijking: MQ DevEngine vs Vibe Kanban

| Aspect | MQ DevEngine | Vibe Kanban |
|--------|-------------|-------------|
| **Backend** | Python (FastAPI) | Rust (Axum) |
| **Frontend** | React 19 + Tailwind v4 | React 18 + Custom CSS |
| **Agent model** | CLI subprocess | CLI subprocess |
| **Agents** | Claude SDK only | 9 agents (Claude, Codex, etc.) |
| **Feature tracking** | SQLite + MCP server | PostgreSQL + MCP server |
| **Real-time** | WebSocket (custom events) | WebSocket + JSON Patch |
| **Isolation** | Process-level | Git worktree |
| **State mgmt** | TanStack Query | Zustand + TanStack Query + DB |
| **Design** | Neobrutalism | Corporate IBM Plex |
| **Scope** | Full lifecycle (spec→build→test) | Task management + execution |

### 4.1 Wat Vibe Kanban Beter Doet

1. **Multi-agent support**: 9 agents vs onze 1 (Claude). Dit is waar Pi Agent helpt -- het voegt 20+ providers toe.
2. **Git worktree isolatie**: Eleganter dan ons process-level isolatie. Agents kunnen niet elkaars code overschrijven.
3. **JSON Patch**: Efficienter dan onze volledige WebSocket berichten. Alleen delta's sturen.
4. **Zustand + TanStack DB**: Robuustere client-side state dan onze huidige aanpak.

### 4.2 Wat MQ DevEngine Beter Doet

1. **Full lifecycle**: Spec creation → feature decomposition → implementation → testing → review. Vibe Kanban doet alleen execution.
2. **Structured agent types**: Architect, Initializer, Coding, Testing, Reviewer -- elk met eigen prompt, tools, en model tier.
3. **Security model**: Defense-in-depth met bash allowlists, filesystem sandboxing, MCP tool scoping. Vibe Kanban heeft dit niet.
4. **Token optimalisatie**: Playwright tiers, scoped permissions, scoped builtin tools per agent type.
5. **Dependency-aware scheduling**: Features worden in volgorde geimplementeerd op basis van afhankelijkheden.
6. **Session memory**: Agents delen context via memory MCP tools.

### 4.3 Conclusie: Zijn We Op De Goede Weg?

**Ja, MQ DevEngine is op de goede weg.** De architectuur is fundamenteel juist:

1. **Subprocess model is de industriestandaard** -- Vibe Kanban, OpenClaw, en alle grote platforms gebruiken hetzelfde patroon.
2. **MCP voor feature tracking** -- Vibe Kanban doet exact hetzelfde.
3. **WebSocket voor real-time** -- universeel patroon.
4. **Agent type differentiatie** -- dit heeft Vibe Kanban NIET. Onze architect/initializer/coding/testing/reviewer pipeline is een significante voorsprong.
5. **Security model** -- Vibe Kanban mist dit volledig. Onze allowlist-gebaseerde aanpak is productie-waardig.

---

## 5. Concreet Actieplan

### Fase 1: Pi Agent als Alternatieve Runtime (Sprint 8.x)

**Prioriteit: Medium** | **Effort: 2-3 dagen** | **Risico: Laag (achter feature flag)**

| # | Taak | Detail |
|---|------|--------|
| 1.1 | `PiAgentRuntime` klasse | Implementeer AgentClient protocol met Pi RPC mode in `agent_runtime.py` |
| 1.2 | Provider routing | In `provider_config.py`: route naar Pi voor Sonnet/Haiku, Claude SDK voor Opus |
| 1.3 | Event mapping | Map Pi events (text, tool_use, error) naar DevEngine's interne format |
| 1.4 | Feature flag | `PI_RUNTIME_ENABLED=1` in `.env`, default uit |
| 1.5 | Smoke test | Coding agent met Pi runtime op een testproject |

### Fase 2: Git Worktree Isolatie (Sprint 8.x)

**Prioriteit: Hoog** | **Effort: 1-2 dagen** | **Risico: Laag**

| # | Taak | Detail |
|---|------|--------|
| 2.1 | Worktree lifecycle | `git worktree add` bij agent start, `git worktree remove` na completion |
| 2.2 | Merge strategie | Na succesvolle feature: merge worktree branch terug naar main |
| 2.3 | Conflict handling | Bij merge conflict: markeer feature als "needs_merge", toon in UI |
| 2.4 | Parallel mode | Elke parallel agent krijgt eigen worktree (vervangt process isolatie) |

### Fase 3: Multi-Provider Support via Pi (Sprint 9.x)

**Prioriteit: Medium** | **Effort: 3-5 dagen** | **Risico: Medium**

| # | Taak | Detail |
|---|------|--------|
| 3.1 | Model routing tabel | Per agent type + taak complexiteit → model selectie |
| 3.2 | Cost tracking | Pi rapporteert token usage per model; aggregeer in DevEngine |
| 3.3 | Failover chain | Claude → OpenAI → Gemini → local Ollama |
| 3.4 | UI model selector | Per agent type het model kunnen kiezen in Settings |

### Fase 4: JSON Patch Real-time Updates (Sprint 9.x)

**Prioriteit: Laag** | **Effort: 2 dagen** | **Risico: Laag**

| # | Taak | Detail |
|---|------|--------|
| 4.1 | JSON Patch library | `jsonpatch` (Python) + `fast-json-patch` (TypeScript) |
| 4.2 | Delta berekening | Server berekent diff tussen vorige en huidige state |
| 4.3 | Client-side apply | TanStack Query cache updaten met patches |

---

## 6. Niet Doen (Bewuste Keuzes)

| Wat | Waarom Niet |
|-----|------------|
| Rust backend | Python FastAPI is productief genoeg, Rust switch is maanden werk |
| Zustand | TanStack Query is voldoende voor onze state complexity |
| Lexical editor | Onze markdown rendering (react-markdown) werkt prima |
| ElectricSQL | Overkill voor onze single-server architectuur |
| Pi Desktop (Tauri) | We zijn web-first, geen desktop app nodig |

---

## 7. Referenties

- [Pi Agent Blog](https://lucumr.pocoo.org/2025/6/13/pi-agent/) - Armin Ronacher
- [Pi Mono Repo](https://github.com/badlogic/pi-mono) - Source code
- [Vibe Kanban](https://github.com/BloopAI/vibe-kanban) - Source code
- [OpenClaw](https://openclaw.com) - Pi Agent headless embedding voorbeeld
- [MQ DevEngine agent_runtime.py](./agent_runtime.py) - Onze abstractielaag die Pi integratie mogelijk maakt
