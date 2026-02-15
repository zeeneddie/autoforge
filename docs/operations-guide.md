# Operations Guide

## Overzicht

MQ DevEngine draait in combinatie met drie componenten:

| Component | Rol | Standaard URL |
|-----------|-----|---------------|
| **MQ Planning** | Project management, sprint cycles, work items | `http://localhost:8080` |
| **MQ DevEngine** | Autonoom coding platform, agent orchestratie | `http://localhost:8888` |
| **Claude CLI** | LLM backend voor de coding/testing/initializer agents | N/A (CLI tool) |

De opstartvolgorde is: MQ Planning → MQ DevEngine → Sync configureren → Agent starten.

---

## MQ Planning opstarten (Docker)

MQ Planning (Plane) draait als een set Docker containers. Start vanuit de Plane project directory:

```bash
cd /home/eddie/Projects/plane
docker compose up -d
```

### Bekende issues

**`docker-compose` v1 vs v2** — Als `docker-compose` (v1) een YAML-fout geeft over `restart: "no"`, gebruik dan `docker compose` (v2, zonder streepje) of verander `"no"` naar `never` in de compose file.

**Containers starten niet allemaal** — Als sommige containers niet opstarten na `docker compose up -d`, start ze individueel:

```bash
# Bekijk welke containers gestopt zijn
docker ps -a --filter "name=plane"

# Start individuele containers
docker start <container_id>
```

### Verificatie

- Open `http://localhost:8080` in de browser
- De MQ Planning login pagina moet zichtbaar zijn
- Data wordt persistent opgeslagen in het `plane_pgdata` Docker volume

---

## MQ DevEngine opstarten

### Vanuit source (development)

```bash
cd /home/eddie/Projects/mq-devEngine
./start_ui.sh
```

Of direct via uvicorn:

```bash
./venv/bin/python -m uvicorn server.main:app --host 0.0.0.0 --port 8888
```

### Via npm (geinstalleerd)

```bash
mq-devengine
```

### Verificatie

- Open `http://localhost:8888` in de browser
- Het kanban board moet zichtbaar zijn

---

## Environment configuratie (.env)

Het `.env` bestand wordt door MQ DevEngine gelezen bij het opstarten en configureert o.a. het LLM backend, Playwright browser settings, en optionele integraties.

### Bestandslocatie

Het `.env` bestand leeft in de MQ DevEngine data directory:

```
~/.mq-devengine/.env
```

In een **development omgeving** (werken vanuit source) moet dit bestand gesymlinkt worden naar de project root, zodat de server het kan vinden:

```bash
ln -s ~/.mq-devengine/.env /pad/naar/mq-devEngine/.env
```

> **Zonder deze symlink leest de dev server geen environment variabelen.** Bij een npm-installatie (`mq-devengine` commando) wordt dit automatisch afgehandeld.

Een `.env.example` in de project root bevat alle beschikbare opties met uitleg.

### LLM backend kiezen

Het `.env` bestand bepaalt welk LLM backend de agents gebruiken. Standaard gebruikt MQ DevEngine de **Claude CLI** (geen extra `.env` configuratie nodig). Alternatieve backends worden geconfigureerd door de relevante sectie in `.env` te uncommenten:

| Backend | Vereiste variabelen |
|---------|-------------------|
| **Claude CLI** (default) | Geen — werkt out of the box na `claude login` |
| **Google Vertex AI** | `CLAUDE_CODE_USE_VERTEX=1`, `CLOUD_ML_REGION`, `ANTHROPIC_VERTEX_PROJECT_ID` |
| **GLM (Zhipu AI)** | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, model namen |
| **Ollama (lokaal)** | `ANTHROPIC_BASE_URL=http://localhost:11434`, `ANTHROPIC_AUTH_TOKEN=ollama` |

Zorg dat slechts **een** backend tegelijk actief is — commentarieer de rest uit.

### Bekende beperkingen niet-Claude modellen

De volgende problemen gelden voor **alle niet-Claude modellen**, ongeacht of ze via OpenRouter, Ollama, of GLM (Zhipu) worden aangesproken. De oorzaak is steeds dezelfde: MQ DevEngine is gebouwd op de Claude Agent SDK en het Anthropic tool use formaat. Niet-Claude modellen ondersteunen dit formaat niet of niet volledig, zelfs als ze via een Anthropic-compatibele API worden aangeboden.

#### MCP tool calls werken niet (of slecht)

MQ DevEngine agents communiceren met de features database via MCP server tools (bijv. `feature_claim_and_get`, `feature_mark_passing`). Deze tool calls gebruiken het Anthropic tool use formaat.

- **GLM modellen** (glm-4.7 etc.) via Zhipu API of OpenRouter: Tool calls worden niet herkend of incorrect teruggegeven. De agent kan features niet claimen, geen status updates doen, en loopt vast.
- **Codex/GPT modellen** via OpenRouter: Gebruiken OpenAI's function calling formaat, niet Anthropic's tool use formaat. OpenRouter vertaalt dit niet altijd correct, waardoor MCP tool responses malformed zijn.
- **Ollama modellen** (qwen3-coder, deepseek-coder, etc.): Ollama biedt sinds v0.14.0 een Anthropic-compatibele API aan, maar de onderliggende modellen zijn niet getraind op Anthropic's tool use schema. Tool calls worden vaak genegeerd, incorrect geformateerd, of de parameters kloppen niet.
- **Symptoom**: De agent genereert code maar kan geen interactie hebben met het kanban board. Features blijven op "Todo" staan, of de agent herhaalt dezelfde actie eindeloos.

#### Extended context niet beschikbaar

MQ DevEngine gebruikt de `context-1m-2025-08-07` beta voor 1M token context windows. Dit wordt automatisch uitgeschakeld voor alle niet-Claude backends (code in `client.py`), wat betekent:

- Kortere context windows (model-afhankelijk — Ollama modellen hebben vaak 8K-128K)
- Bij langere sessies raakt de agent context kwijt
- Grotere codebases passen mogelijk niet in het context window
- Ollama modellen zijn hier het meest beperkt: lokale hardware bepaalt hoeveel context het model aankan

#### Streaming en response formaat

Niet-Claude modellen hebben soms afwijkend streaming gedrag of retourneren responses in een net iets ander formaat, wat kan leiden tot:

- Parsing errors in de Agent SDK
- Onverwacht afgebroken responses
- Verlies van gestructureerde output (JSON tool responses)

Dit geldt zowel voor OpenRouter (vertaallaag tussen providers) als Ollama (lokale Anthropic API compatibiliteitslaag).

#### Aanbeveling

Gebruik **Claude modellen** voor productie-werk:
- **Direct via CLI** (`claude login`) — meest betrouwbaar
- **Via OpenRouter** met `anthropic/claude-*` model IDs — werkt, maar extra latency
- **Via Vertex AI** — voor GCP omgevingen

Niet-Claude modellen (OpenRouter, Ollama, GLM) zijn bruikbaar voor experimenten met text generation, maar de MCP tool integratie — essentieel voor het agent workflow — is alleen betrouwbaar met Claude.

### Overige .env opties

| Variabele | Default | Beschrijving |
|-----------|---------|-------------|
| `PLAYWRIGHT_BROWSER` | `firefox` | Browser engine: `firefox`, `chrome`, `webkit`, `msedge` |
| `PLAYWRIGHT_HEADLESS` | `true` | `false` = browser zichtbaar (debugging) |
| `EXTRA_READ_PATHS` | leeg | Comma-separated paden die agents mogen lezen |
| `AUTOFORGE_ALLOW_REMOTE` | niet gezet | Zet op `1` om remote access toe te staan (niet alleen localhost) |
| `API_TIMEOUT_MS` | library default | Request timeout in ms |

---

## Claude CLI configuratie

Bij gebruik van de Claude CLI als LLM backend (standaard):

### Authenticatie

```bash
claude login
```

Dit vereist een Claude Pro of Max abonnement.

### Verificatie

```bash
mq-devengine config --show
```

Controleer dat het juiste model geselecteerd is en dat de authenticatie werkt.

---

## Planning Sync configureren

### Via de MQ DevEngine UI

Open Settings (tandwiel icoon) in de MQ DevEngine UI en vul de MQ Planning sectie in:

| Setting | Beschrijving | Voorbeeld |
|---------|-------------|-----------|
| `planning_api_url` | MQ Planning API base URL | `http://localhost:8080/api/v1` |
| `planning_api_key` | MQ Planning API key (uit MQ Planning profiel settings) | `plane_api_...` |
| `planning_workspace_slug` | Workspace slug in MQ Planning | `my-workspace` |
| `planning_project_id` | Project UUID in MQ Planning | `a1b2c3d4-...` |
| `planning_cycle_id` | Active cycle UUID in MQ Planning | `e5f6g7h8-...` |

De API key is te vinden in MQ Planning onder: **Profile → Settings → API Tokens**.

### Via registry (CLI)

Settings worden opgeslagen in `~/.mq-devengine/registry.db`. Ze kunnen ook direct via de API gezet worden:

```bash
curl -X PATCH http://localhost:8888/api/settings \
  -H "Content-Type: application/json" \
  -d '{"plane_api_url": "http://localhost:8080/api/v1", "plane_api_key": "..."}'
```

### Sync starten

- **Via UI:** Toggle de sync schakelaar in de Settings modal (MQ Planning sectie)
- **Via API:** `POST http://localhost:8888/api/planning/sync/toggle`

> **WAARSCHUWING: Globale sync bij meerdere projecten**
>
> De Planning sync configuratie is momenteel **globaal** — niet per project. Als je meerdere projecten hebt geregistreerd (bijv. `klaverjas_app` en `mq-discovery`), importeert de sync loop work items uit de geconfigureerde MQ Planning cycle naar **alle** projecten. Dit veroorzaakt cross-project data lekkage.
>
> **Workaround:** Disable sync (`planning_sync_enabled=false`) wanneer meerdere projecten geregistreerd zijn. Gebruik handmatige import via `POST /api/planning/import-cycle` per project.
>
> **Fix:** Per-project sync configuratie is gepland in Sprint 7.1. Zie [ADR-004](decisions/ADR-004-per-project-plane-sync.md).

---

## Sync werking

### Inbound sync (MQ Planning → MQ DevEngine)

- Haalt work items op uit de geconfigureerde MQ Planning cycle
- Maakt nieuwe MQ DevEngine features aan voor onbekende work items
- Matcht bestaande features op `planning_work_item_id`
- Synchroniseert titel, beschrijving, prioriteit en acceptance criteria

### Outbound sync (MQ DevEngine → MQ Planning)

- Pusht feature status naar het bijbehorende MQ Planning work item:
  - Alle tests passen → state **Done**
  - Tests in progress → state **In Progress**
  - Geen tests → state **Todo**
- Gebruikt een hash (`planning_last_status_hash`) om onnodige API calls te voorkomen

### Echo prevention

Bidirectionele sync kan echo-loops veroorzaken. Dit wordt voorkomen door:

- **Outbound:** `planning_last_status_hash` slaat `"{passes}:{in_progress}"` op — skip als hash ongewijzigd
- **Inbound:** vergelijkt MQ Planning `updated_at` met opgeslagen `planning_updated_at` — skip als gelijk (eigen update die terugkomt)

### Interval

De sync loop draait elke **30 seconden** (configureerbaar). Elke iteratie voert zowel inbound als outbound sync uit.

### Let op

Features die al bestonden in MQ DevEngine voor de sync werd geconfigureerd, worden **niet** automatisch gelinkt aan MQ Planning work items. Deze moeten handmatig gekoppeld worden door de `planning_work_item_id` te zetten.

---

## Agent starten

### Via de UI

Klik op **Start** op het kanban board. De orchestrator start dan de agent pipeline:

1. **Initializer** — maakt features aan uit de `app_spec.txt` (als er nog geen features zijn)
2. **Coding agents** — implementeert features parallel
3. **Testing agents** — voert regression tests uit na elke coding ronde

### Via de API

```bash
curl -X POST http://localhost:8888/api/projects/<project_name>/agent/start \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-sonnet-4-5-20250929"}'
```

### Agent stoppen

Er zijn twee manieren om een agent te stoppen:

**Soft stop (graceful):** Agents ronden lopend werk af, claimen geen nieuwe features, en stoppen daarna automatisch. Geen half-geschreven code.

```bash
# Via UI: klik de CircleStop knop (outline)
# Via API:
curl -X POST http://localhost:8888/api/projects/<project_name>/agent/soft-stop
```

De status gaat naar `finishing`. De UI toont een "Finishing..." badge met spinner. Hard stop blijft beschikbaar als noodknop.

**Hard stop (direct):** Doodt de hele process tree onmiddellijk. Lopende agents worden afgebroken.

```bash
# Via UI: klik de rode Square knop
# Via API:
curl -X POST http://localhost:8888/api/projects/<project_name>/agent/stop
```

### Verificatie

- Het kanban board toont features die van **Todo** → **In Progress** → **Passing** gaan
- De terminal/logs tonen agent output per subprocess
- Als Planning sync actief is, worden statuswijzigingen automatisch naar MQ Planning gepusht

---

## Troubleshooting

### MQ Planning containers gestopt

```bash
# Bekijk status
docker ps -a --filter "name=plane"

# Start alle gestopte containers
docker start $(docker ps -a --filter "name=plane" --filter "status=exited" -q)
```

### Port 80 in gebruik

MQ Planning (Plane) probeert standaard poort 80 te gebruiken. Als deze bezet is, pas de proxy poort aan in de Docker Compose configuratie. De standaard workaround is poort 8080.

### Agent crasht direct

1. Controleer de Claude CLI versie: `claude --version`
2. Verifieer authenticatie: `claude login`
3. Check of het model beschikbaar is in de settings
4. Bekijk de agent logs in de terminal output

### Sync pusht niet naar MQ Planning

Als de outbound sync geen updates stuurt terwijl de status veranderd is:

1. Controleer of de sync actief is: `GET http://localhost:8888/api/planning/sync-status`
2. De hash kan out-of-sync zijn. Reset door de feature status te wijzigen (bijv. een test opnieuw laten draaien)
3. Controleer de MQ Planning API key geldigheid
4. Bekijk de server logs voor API fouten

### Features niet gelinkt na sync

Features die bestonden voor de Planning sync was geconfigureerd, worden niet automatisch gekoppeld. Koppel ze handmatig via de database of door de feature te verwijderen en opnieuw te laten importeren via de sync.
