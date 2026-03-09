# PRD: Sudoku Solver Web App (Rebuild)

## Doel

Herbouw van de sudoku-solver als testproject voor MQ DevEngine verbeteringen:
- **Agent log persistence** — verifieer dat tool calls, thinking en code-output nu in de DB terechtkomen
- **TDD mode** — test de Red/Green/Refactor cycle met geautomatiseerde tests
- **Batch feature attribution** — verifieer dat logs correct per feature worden geattribueerd

## Product Omschrijving

Een interactieve Sudoku-puzzel webapp waarmee gebruikers:
1. Een nieuw Sudoku-puzzel kunnen genereren (easy/medium/hard)
2. Het puzzel interactief kunnen oplossen in de browser
3. Hints kunnen vragen (volgende correcte zet)
4. De oplossing kunnen bekijken
5. Input-validatie krijgen (conflicten markeren)

## Technische Stack

- **Frontend**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS v4
- **State**: React useState/useReducer (geen externe state library nodig)
- **Testing**: Vitest + React Testing Library (TDD mode)
- **Geen backend nodig** — alle logica client-side

## Features (verwacht ~7-10)

### Infrastructure (1-5)
1. Project setup: Vite + React + TypeScript + Tailwind
2. Vitest + RTL geconfigureerd met sample test
3. Base layout en grid component (9x9)
4. Sudoku data model (board state, given vs user cells)
5. Cell input component met keyboard navigatie

### Core Logic (6-8)
6. Puzzel generator (backtracking solver + cell removal)
7. Conflict detectie (rij/kolom/blok validatie)
8. Hint systeem (volgende correcte cel invullen)

### UX Polish (9-10)
9. Moeilijkheidsgraad selector (easy/medium/hard)
10. Win-detectie en felicitatie

## Acceptatiecriteria

### Agent Log Persistence (primair testdoel)
- [ ] Na voltooiing: `agent_logs` tabel bevat tool calls (`[Tool: Write]`, `[Tool: Bash]`, etc.)
- [ ] Logs bevatten thinking blocks en text responses
- [ ] Bij batch mode: features 2+ hebben eigen log entries (niet alles op feature #1)
- [ ] CLI run (zonder WebSocket) produceert dezelfde logs als UI run

### TDD Mode
- [ ] Test framework feature (#2) wordt als eerste infrastructure feature aangemaakt
- [ ] Coding agents schrijven tests VOOR implementatie (red phase)
- [ ] `feature_record_test` MCP tool wordt aangeroepen met test resultaten
- [ ] Alle features hebben `test_file_path` en `test_count` ingevuld na completion

## MQ DevEngine Instellingen

```
TDD Mode:        enabled
YOLO Mode:       disabled (we willen volledige test verification)
Batch Size:      1 (voor betere log attribution testing)
Concurrency:     1 (voor eerste test, later ophogen)
Model:           default (sonnet)
```

## Verificatie Plan

### Stap 1: Project aanmaken
```bash
# Via UI of CLI
mq-devengine
# → New Project → "sudoku-solver-v2" → pad kiezen
```

### Stap 2: Spec genereren
```
/create-spec
# → verwijs naar deze PRD
# → Quick mode, ~10 features
```

### Stap 3: Agent starten met TDD
- UI: Settings → TDD Mode ON → Start Agent
- CLI: `python3 autonomous_agent_demo.py --project-dir sudoku-solver-v2 --tdd`

### Stap 4: Logs verifiëren
```sql
-- Na eerste feature completion:
SELECT feature_id, run_id, log_type, substr(line, 1, 80)
FROM agent_logs
WHERE feature_id = 1
ORDER BY id DESC
LIMIT 20;

-- Verwacht: [Tool: Write], [Tool: Bash], thinking blocks, text responses
-- NIET alleen: "Starting feature 1/10: #1 - Project setup"
```

### Stap 5: Batch test (optioneel)
```bash
python3 autonomous_agent_demo.py --project-dir sudoku-solver-v2 --tdd --batch-size 3
# Verifieer: features 2 en 3 hebben eigen agent_logs entries
```
