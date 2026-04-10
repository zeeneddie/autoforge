# mq-devEngine — Adversarial Evaluator Plan

> **Eigenaar:** Linus (CTO)
> **Status:** TODO — geplande implementatie Fase 2 (apr-mei 2026)
> **ROADMAP taak:** 2E (na 1C devEngine stabilisatie)
> **Gelinkt aan:** `mq-platform/docs/adversarial-round-table.md` §3.1

---

## Context

Na `feature_validate_quality()` (deterministisch: test count + output-check) wordt een tweede model ingeschakeld als adversariale evaluator. Het generator-model (Sonnet 4.6) heeft dezelfde blinde vlekken als bij het coderen — een model van een andere familie haalt er andere bugs uit.

Dit volgt het **"Ralph Wigum loop"** patroon (max 3 retries) dat al gedocumenteerd is in:
`mq-platform/docs/po-companion-spec-quality-plan.md` §A1

**Opt-in via env var** — als `ADVERSARIAL_EVALUATOR_MODEL` niet is ingesteld, gedraagt de codebase zich exact als nu. Geen breaking change.

---

## Hook point

**Bestand:** `mcp_server/feature_mcp.py`
**Huidige gate:** `feature_validate_quality()` (regel 275–367) — deterministisch (test count ≥ 1, test output bevat "passed")
**Nieuwe gate:** `feature_adversarial_evaluate()` — na validate, vóór `feature_mark_passing()`

```
feature_validate_quality()    [bestaand — deterministisch, altijd actief]
         ↓ passed
feature_adversarial_evaluate()  [NIEUW — optioneel, via ADVERSARIAL_EVALUATOR_MODEL]
         ↓ score ≥ 7
feature_mark_passing()        [bestaand]
```

---

## Nieuwe functie

```python
def feature_adversarial_evaluate(feature_id: int) -> dict:
    """
    Roept een adversariale evaluator aan (via litellm) om de implementatie
    van feature_id te challengen.
    
    Returns: {
        "ok": bool,           # True als score ≥ 7 en geen HIGH issues
        "score": int,         # 1-10
        "issues": list[str],  # Concrete verbeterpunten
        "model_used": str,    # bijv. "gpt-5.4"
        "retries": int        # hoevaak al geprobeerd (max 3)
    }
    """
```

**MCP tool registratie:** `feature_adversarial_evaluate` — naast de bestaande `feature_validate_quality` tool.

---

## DB-velden (hergebruiken — al aanwezig in `api/database.py`)

| Veld | Type | Gebruik |
|---|---|---|
| `review_status` | str | `"pending_review"` \| `"approved"` \| `"rejected"` |
| `review_notes` | Text | Issues van de evaluator (kommalijst of markdown) |
| `reviewed_at` | DateTime | Timestamp van de evaluatie |
| `escalation_reason` | Text | Reden bij `review_status = "rejected"` na 3 retries |

Geen migratie nodig — velden bestaan al.

---

## Model routing

**Via litellm gateway** (al in stack op P920, port 8080).

**Env var:** `ADVERSARIAL_EVALUATOR_MODEL`

| Waarde | Gedrag |
|---|---|
| leeg / niet ingesteld | Skip adversarial evaluate — gedraagt zich als nu |
| `"gpt-5.4"` | GPT-5.4 via litellm → OpenAI API (Codex harness default, sterkste code-reviewer) |
| `"o4-mini"` | o4-mini via litellm → OpenAI API (goedkoper alternatief, goede code-review) |
| `"ollama/qwen2.5-coder"` | Qwen2.5-Coder-14B lokaal op P920 (privacy) |
| `"claude-opus-4-6"` | Opus als evaluator (gebruik sparingly — duur) |

**Toevoeging in `env_constants.py`:**
```python
"ADVERSARIAL_EVALUATOR_MODEL",  # Model for adversarial code review (empty = skip)
```

**Toevoeging in `model_config.py`:** Nieuw role `"evaluator"` naast `coding`, `architect`, `testing`.

---

## Volledige flow

```
feature klaar (generator: Sonnet 4.6)
  → feature_validate_quality()
      ok=False                          → blokkeer (bestaand gedrag)
      ok=True
        → ADVERSARIAL_EVALUATOR_MODEL leeg?
            ja → feature_mark_passing() (bestaand gedrag)
            nee → feature_adversarial_evaluate()
                    score ≥ 7, geen HIGH issues
                        → review_status = "approved"
                        → feature_mark_passing()
                    score < 7
                        → review_notes = issues
                        → generator retry (retries += 1, max 3)
                    retries == 3, nog steeds score < 7
                        → review_status = "rejected"
                        → escalation_reason = issues summary
                        → notificeer Eddie (via mq-brain / console)
```

---

## Score-criteria (1–10, drempel ≥ 7)

De evaluator beoordeelt op:
1. **Code kwaliteit** — leesbaarheid, maintainability, geen dode code
2. **Test coverage** — AC-coverage ≥ 80%, edge cases geadresseerd
3. **Edge cases** — zijn grenzen en foutgevallen gedekt?
4. **Security** — prompt injection, input validatie, geen hardcoded secrets
5. **Architectuur** — past het in het patroon van de codebase?

---

## Implementatievolgorde

| # | Stap | Moeite |
|---|---|---|
| 1 | `ADVERSARIAL_EVALUATOR_MODEL` toevoegen aan `env_constants.py` | 5 min |
| 2 | `"evaluator"` role toevoegen aan `model_config.py` | 15 min |
| 3 | `feature_adversarial_evaluate()` implementeren in `feature_mcp.py` | 1 dag |
| 4 | MCP tool registreren + feature-flow updaten | 1 uur |
| 5 | Tests schrijven (geen mock van LLM calls — mq-devEngine is strict) | 1 dag |
| 6 | **Fase 1 activeren**: `ADVERSARIAL_EVALUATOR_MODEL=gpt-5.4`, blokkeert NIET | 5 min |
| 7 | litellm route configureren: adversarial-evaluator → gpt-5.4 (2E.4) | 30 min |
| 8 | Na 2 weken stabiel: **Fase 2 activeren** — blokkeer bij score < 7 | 1 uur |

**Totale moeite:** ~2 dagen implementatie + 1 dag testen

---

## Blockers voor start

- **1C moet klaar zijn:** devEngine stabilisatie (Glob-bug, CLI model settings) — geen features bouwen in instabiele codebase
- **litellm route:** `ADVERSARIAL_EVALUATOR_MODEL=gpt-5.4` vereist een werkende litellm instance met OpenAI API key configuratie
- **Fase 1 eerst:** blokkeer NIET bij activatie — eerst baseline data verzamelen

---

## Fase-schema (progressief vertrouwen)

| Fase | ADVERSARIAL_EVALUATOR_MODEL | Blokkeer bij | Activatiedrempel |
|---|---|---|---|
| **0 (nu)** | leeg | — | — |
| **1 (rapport)** | gpt-5.4 | nooit | activeer na 2E.3 |
| **2 (gate)** | gpt-5.4 | score < 7 | gem. score ≥ 7.5 over 4 weken |
| **3 (autonoom)** | gpt-5.4 + escalatie | score < 5 | 3 maanden stabiel |

---

## Monitoringdata voor Linus review

Alle adversarial evaluaties worden gelogd via bestaande `review_status` / `review_notes` / `reviewed_at` velden. Linus leest deze data maandelijks (zie `mq-brain/hq/identities/linus/HEARTBEAT.md` → `model_quality_review` trigger).

Aanvullende logging:
- `model_used` opslaan in `review_notes` header: `<!-- model: gpt-5.4, score: 7, retries: 1 -->`
- Feature-complexiteit label (`ac_labels`) helpt Linus onderscheid te maken: faalden simpele of complexe features?
