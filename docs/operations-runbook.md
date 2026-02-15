# Operations Runbook: Omgevingen Starten & Stoppen

> PID tracking en verificatie voor alle MarQed.ai componenten.

## Overzicht Componenten

| Component | Port | Start methode | PID tracking |
|---|---|---|---|
| MQ Planning (Docker Compose) | 8080 (proxy), 8082 (API), 5433 (DB), 6380 (Redis), 9001 (MinIO) | Docker Compose | Container names |
| ChromaDB | 8001 | Docker container | Container name |
| MQ DevEngine Server | 8888 | Python uvicorn | PID file |
| MQ DevEngine UI (dev) | 5175 | Vite dev server | PID file |
| MQ DevEngine Agent(s) | - | Subprocess via API | Agent status API |

## PID File Locatie

Alle PID files worden opgeslagen in `~/.mq-devengine/pids/`:

```bash
mkdir -p ~/.mq-devengine/pids
```

---

## 1. MQ Planning (Docker Compose)

### Starten

```bash
cd /home/eddie/plane
docker compose -f docker-compose-local.yml up -d
```

### Verificatie

```bash
# Alle containers moeten "Up" zijn
docker ps --filter "name=plane" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health check
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/  # verwacht: 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8082/  # verwacht: 200 (API)
```

### Stoppen

```bash
cd /home/eddie/plane
docker compose -f docker-compose-local.yml down
```

### Verificatie na stoppen

```bash
docker ps --filter "name=plane" --format "{{.Names}}"  # verwacht: leeg
ss -tlnp | grep -E '8080|8082|5433|6380|9001'          # verwacht: leeg
```

---

## 2. ChromaDB

### Starten

```bash
docker start project_manager_chromadb
```

### Verificatie

```bash
docker ps --filter "name=project_manager_chromadb" --format "{{.Names}}\t{{.Status}}"
curl -s http://localhost:8001/api/v1/heartbeat  # verwacht: {"nanosecond heartbeat":...}
```

### Stoppen

```bash
docker stop project_manager_chromadb
```

### Verificatie na stoppen

```bash
docker ps --filter "name=project_manager_chromadb" --format "{{.Names}}"  # verwacht: leeg
```

---

## 3. MQ DevEngine Server

### Starten

```bash
cd /home/eddie/Projects/mq-devEngine
nohup ./venv/bin/python -m server.main > /tmp/devengine-server.log 2>&1 &
echo $! > ~/.mq-devengine/pids/server.pid
echo "MQ DevEngine Server PID: $(cat ~/.mq-devengine/pids/server.pid)"
```

### Verificatie

```bash
# PID check
PID=$(cat ~/.mq-devengine/pids/server.pid 2>/dev/null)
ps -p $PID -o pid,cmd --no-headers 2>/dev/null || echo "Process NOT running"

# Port check
ss -tlnp | grep 8888

# Health check
curl -s http://localhost:8888/api/health  # verwacht: {"status":"healthy"}
```

### Stoppen

```bash
PID=$(cat ~/.mq-devengine/pids/server.pid 2>/dev/null)
if [ -n "$PID" ]; then
    kill $PID 2>/dev/null
    sleep 2
    # Controleer of gestopt
    if ps -p $PID > /dev/null 2>&1; then
        echo "WARN: Process $PID still running, sending SIGKILL"
        kill -9 $PID 2>/dev/null
    fi
    rm -f ~/.mq-devengine/pids/server.pid
    echo "Server stopped"
else
    echo "No PID file found"
fi
```

### Verificatie na stoppen

```bash
PID=$(cat ~/.mq-devengine/pids/server.pid 2>/dev/null)
ps -p $PID > /dev/null 2>&1 && echo "FAIL: still running" || echo "OK: stopped"
ss -tlnp | grep 8888  # verwacht: leeg
curl -s http://localhost:8888/api/health  # verwacht: connection refused
```

---

## 4. MQ DevEngine UI (Development)

### Starten

```bash
cd /home/eddie/Projects/mq-devEngine/ui
nohup npm run dev > /tmp/devengine-ui.log 2>&1 &
echo $! > ~/.mq-devengine/pids/ui.pid
echo "MQ DevEngine UI PID: $(cat ~/.mq-devengine/pids/ui.pid)"
```

### Verificatie

```bash
PID=$(cat ~/.mq-devengine/pids/ui.pid 2>/dev/null)
ps -p $PID -o pid,cmd --no-headers 2>/dev/null || echo "Process NOT running"
ss -tlnp | grep 5175
curl -s -o /dev/null -w "%{http_code}" http://localhost:5175/  # verwacht: 200
```

### Stoppen

```bash
PID=$(cat ~/.mq-devengine/pids/ui.pid 2>/dev/null)
if [ -n "$PID" ]; then
    kill $PID 2>/dev/null
    sleep 2
    if ps -p $PID > /dev/null 2>&1; then
        kill -9 $PID 2>/dev/null
    fi
    rm -f ~/.mq-devengine/pids/ui.pid
    echo "UI stopped"
fi
```

---

## 5. MQ DevEngine Agent (per project)

Agents worden gestart/gestopt via de MQ DevEngine API.

### Starten

```bash
# Start agent voor een project (1 agent, 1 item per keer)
curl -s -X POST http://localhost:8888/api/projects/PROJECT_NAME/agent/start \
  -H "Content-Type: application/json" \
  -d '{"max_concurrency": 1, "batch_size": 1}' | python3 -m json.tool
```

### Status checken

```bash
curl -s http://localhost:8888/api/projects/PROJECT_NAME/agent/status | python3 -m json.tool
```

### Stoppen (graceful)

Agents ronden lopend werk af, stoppen daarna automatisch:

```bash
curl -s -X POST http://localhost:8888/api/projects/PROJECT_NAME/agent/soft-stop | python3 -m json.tool
# Status gaat naar "finishing", daarna automatisch "stopped"
```

### Stoppen (hard / noodknop)

Doodt de hele process tree direct:

```bash
curl -s -X POST http://localhost:8888/api/projects/PROJECT_NAME/agent/stop | python3 -m json.tool
```

---

## 6. Quick Scripts

### Alles starten (behalve agents)

```bash
#!/bin/bash
set -e
mkdir -p ~/.mq-devengine/pids

echo "=== Starting MQ Planning ==="
cd /home/eddie/plane
docker compose -f docker-compose-local.yml up -d

echo "=== Starting ChromaDB ==="
docker start project_manager_chromadb 2>/dev/null || echo "Already running"

echo "=== Starting MQ DevEngine Server ==="
cd /home/eddie/Projects/mq-devEngine
if ss -tlnp | grep -q ':8888 '; then
    echo "Server already running on port 8888"
else
    nohup ./venv/bin/python -m server.main > /tmp/devengine-server.log 2>&1 &
    echo $! > ~/.mq-devengine/pids/server.pid
    sleep 3
fi

echo "=== Starting MQ DevEngine UI ==="
cd /home/eddie/Projects/mq-devEngine/ui
if ss -tlnp | grep -q ':5175 '; then
    echo "UI already running on port 5175"
else
    nohup npm run dev > /tmp/devengine-ui.log 2>&1 &
    echo $! > ~/.mq-devengine/pids/ui.pid
    sleep 2
fi

echo ""
echo "=== Status ==="
echo "Planning: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/)"
echo "ChromaDB: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/api/v1/heartbeat)"
echo "Server:   $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8888/api/health)"
echo "UI:       $(curl -s -o /dev/null -w '%{http_code}' http://localhost:5175/)"
```

### Alles stoppen

```bash
#!/bin/bash
echo "=== Stopping Agents ==="
for project in klaverjas_app mq-discovery; do
    STATUS=$(curl -s http://localhost:8888/api/projects/$project/agent/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null)
    if [ "$STATUS" = "running" ] || [ "$STATUS" = "finishing" ]; then
        curl -s -X POST http://localhost:8888/api/projects/$project/agent/stop
        echo "  $project: stopped"
    else
        echo "  $project: not running"
    fi
done

echo "=== Stopping MQ DevEngine UI ==="
PID=$(cat ~/.mq-devengine/pids/ui.pid 2>/dev/null)
[ -n "$PID" ] && kill $PID 2>/dev/null && rm -f ~/.mq-devengine/pids/ui.pid && echo "  UI stopped (PID $PID)"

echo "=== Stopping MQ DevEngine Server ==="
PID=$(cat ~/.mq-devengine/pids/server.pid 2>/dev/null)
[ -n "$PID" ] && kill $PID 2>/dev/null && rm -f ~/.mq-devengine/pids/server.pid && echo "  Server stopped (PID $PID)"

echo "=== Stopping ChromaDB ==="
docker stop project_manager_chromadb 2>/dev/null && echo "  ChromaDB stopped"

echo "=== Stopping MQ Planning ==="
cd /home/eddie/plane
docker compose -f docker-compose-local.yml down && echo "  MQ Planning stopped"

echo ""
echo "=== Verificatie ==="
sleep 2
echo "Port 8080 (Planning): $(ss -tlnp | grep -c ':8080 ') listeners"
echo "Port 8001 (ChromaDB): $(ss -tlnp | grep -c ':8001 ') listeners"
echo "Port 8888 (Server):   $(ss -tlnp | grep -c ':8888 ') listeners"
echo "Port 5175 (UI):       $(ss -tlnp | grep -c ':5175 ') listeners"
echo "PID files remaining:  $(ls ~/.mq-devengine/pids/ 2>/dev/null | wc -l)"
```

### Status check

```bash
#!/bin/bash
echo "=== Omgevingen Status ==="
echo ""

# MQ Planning
PLANNING_STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/ 2>/dev/null)
PLANNING_CONTAINERS=$(docker ps --filter "name=plane" --format "{{.Names}}" 2>/dev/null | wc -l)
echo "Planning:  HTTP $PLANNING_STATUS ($PLANNING_CONTAINERS containers)"

# ChromaDB
CHROMA_STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/api/v1/heartbeat 2>/dev/null)
echo "ChromaDB:  HTTP $CHROMA_STATUS"

# Server
SERVER_PID=$(cat ~/.mq-devengine/pids/server.pid 2>/dev/null)
SERVER_STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8888/api/health 2>/dev/null)
echo "Server:    HTTP $SERVER_STATUS (PID: ${SERVER_PID:-none})"

# UI
UI_PID=$(cat ~/.mq-devengine/pids/ui.pid 2>/dev/null)
UI_STATUS=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5175/ 2>/dev/null)
echo "UI:        HTTP $UI_STATUS (PID: ${UI_PID:-none})"

echo ""
echo "=== Agent Status ==="
for project in klaverjas_app mq-discovery; do
    AGENT=$(curl -s http://localhost:8888/api/projects/$project/agent/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unavailable'))" 2>/dev/null || echo "unavailable")
    echo "  $project: $AGENT"
done
```
