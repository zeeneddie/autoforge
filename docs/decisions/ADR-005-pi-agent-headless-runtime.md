# ADR-005: Pi Agent als Headless Alternatieve Runtime

**Status:** Proposed
**Datum:** 2026-02-28
**Context:** Onderzoek naar multi-runtime agent architectuur

## Besluit

Pi Agent kan headless worden aangestuurd als alternatieve runtime naast de Claude Agent SDK. OpenClaw bewijst dit in productie via hun `PiEmbeddedRunner`.

Onze `agent_runtime.py` abstractielaag (AgentClient protocol) maakt het mogelijk om een `PiAgentRuntime` toe te voegen zonder wijzigingen in `agent.py`, `client.py`, of de chat sessions.

## Context

### Huidige Architectuur

```
parallel_orchestrator.py → subprocess → agent.py → ClaudeAgentRuntime → Claude SDK
```

Alle Claude SDK imports zijn geisoleerd in `agent_runtime.py` achter het `AgentClient` protocol.

### Pi Agent Headless Bewijs

OpenClaw embed Pi Agent direct als npm library:
1. Importeert `@mariozechner/pi-agent-core`
2. Start sessions programmatisch via `createAgentSession()`
3. Subscribed op events voor real-time updates
4. Stuurt bij via `steer()` en `followUp()`

Pi Agent heeft ook een **RPC mode** (JSON over stdin/stdout) die integratie vanuit Python triviaal maakt.

### Integratie Opties

**Optie A - RPC Mode (aanbevolen):**
- Start Pi als child process in RPC mode
- Communiceer via JSON over stdin/stdout
- Geen Node.js dependency in Python runtime nodig
- Werkt met elke Pi versie

**Optie B - SDK via Node subprocess:**
- Schrijf een thin Node.js wrapper die Pi SDK importeert
- Python communiceert met Node wrapper via IPC
- Meer controle, meer complexiteit

## Consequenties

### Positief
- 20+ LLM providers beschikbaar (niet alleen Claude)
- Per-agent model selectie (goedkopere modellen voor simpele taken)
- Failover bij API outages
- Session trees met branching en auto-compaction

### Negatief
- Extra dependency (Node.js + Pi Agent npm package)
- Event format conversie nodig (Pi events → DevEngine format)
- Security model moet dubbel gevalideerd worden (onze hooks + Pi's sandbox)
- Pi is nog v0.x, API kan breken

### Risico Mitigatie
- Feature flag: `PI_RUNTIME_ENABLED=1`, default uit
- Alleen voor coding agents (niet initializer/reviewer)
- Onze security.py hooks blijven actief op subprocess niveau

## Gerelateerd

- [Uitgebreide analyse](../analysis-pi-agent-vibekanban-integration.md)
- `agent_runtime.py` - AgentClient protocol en ClaudeAgentRuntime
- `provider_config.py` - Multi-provider configuratie
