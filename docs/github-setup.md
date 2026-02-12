# GitHub Setup Runbook — MarQed.ai

## Overzicht

Alle MarQed.ai repositories worden beheerd onder een GitHub Organization.
Dit document beschrijft de complete setup procedure.

---

## Stap 1: GitHub Organization aanmaken

### Optie A: Via CLI (als token `admin:org` scope heeft)

```bash
gh api orgs -X POST -f login="marqed-ai" -f profile_name="MarQed.ai" -f billing_email="<email>"
```

### Optie B: Via web UI

1. Ga naar https://github.com/organizations/plan
2. Kies **Free** plan (upgraden kan later)
3. Organization name: `marqed-ai`
4. Contact email: `<MarQed email>`
5. Kies: **A business or institution**

### Na aanmaak

```bash
# Verifieer org bestaat
gh api orgs/marqed-ai --jq '.login'

# Check je membership
gh api user/orgs --jq '.[].login'
```

### Token scope uitbreiden (indien nodig)

De huidige `gh` token heeft `read:org`. Voor org management is `admin:org` nodig:

```bash
# Vernieuw token met extra scopes
gh auth refresh -s admin:org,delete_repo
```

---

## Stap 2: Repository structuur aanmaken

### Eigen repos

| Repo | Beschrijving | Visibility |
|------|-------------|------------|
| `mq-devEngine` | AutoForge core platform (FastAPI + React, autonoom coding) | Private |
| `mq-discover` | Discovery Tool - AI-powered requirements gathering (brownpaper & greenpaper) | Private |
| `mq-monitor` | PM Dashboard - hierarchical drill-down, metrics, intake portal | Private |
| `mq-onboarding` | Onboarding - codebase analyse, kennis opbouw, IFPUG FP | Private |
| `mq-planning` | Plane SDK abstraction layer - sync, webhooks, cycles | Private |
| `mq-import` | MarQed tree format parser and Plane importer | Private |
| `mq-auth` | Multi-tenant auth service - schema-per-tenant, JWT, RBAC | Private |
| `mq-supervisor` | Meta-agent - process monitoring, stuck detection, quality gates | Private |
| `mq-feedbackLoop` | Feedback loop, knowledge management, traceability | Private |
| `mq-platform` | Platform docs, roadmap, deployment configs, design tokens | Private |

### Aanmaken eigen repos

```bash
# Alle repos zijn al aangemaakt onder marqed-ai org
# Verifieer:
gh repo list marqed-ai --json name,isPrivate --jq '.[] | select(.isFork == false) | "\(.name) (private: \(.isPrivate))"'
```

---

## Stap 3: Forks aanmaken

Elke fork krijgt:
- `UPSTREAM_VERSION` file met gepinde versie
- `AUTOFORGE_CHANGES.md` met onze wijzigingen

### Fork commando's

De volgende forks zijn aangemaakt (upstream naam behouden):

| Fork | Upstream | Doel |
|------|----------|------|
| `plane` | `makeplane/plane` | Project management, self-hosted |
| `litellm` | `BerriAI/litellm` | LLM proxy, multi-provider routing |
| `assistant-ui` | `assistant-ui/assistant-ui` | React AI chat components (Discovery Tool) |

```bash
# Verifieer forks
gh repo list marqed-ai --json name,isFork --jq '.[] | select(.isFork == true) | .name'
```

> **Let op:** De initieel geplande forks voor Playwright, Vitest, Ollama, Allure en BMAD zijn niet aangemaakt — deze worden als dependencies via package managers beheerd in plaats van als forks.

### Fork initialisatie script

Na elke fork, voeg tracking files toe:

```bash
# Herhaal voor elke fork
FORK_REPO="marqed-ai/fork--plane"
UPSTREAM_VERSION="v1.2.0"  # Pin huidige werkende versie

gh repo clone $FORK_REPO /tmp/fork-init
cd /tmp/fork-init

echo "$UPSTREAM_VERSION" > UPSTREAM_VERSION
cat > AUTOFORGE_CHANGES.md << 'EOF'
# AutoForge Changes

Changes made to this fork for MarQed.ai / AutoForge integration.

## Changes

_None yet — upstream pinned at version in UPSTREAM_VERSION._
EOF

git add UPSTREAM_VERSION AUTOFORGE_CHANGES.md
git commit -m "chore: add upstream version tracking"
git push
cd -
rm -rf /tmp/fork-init
```

---

## Stap 4: Fork sync workflow

### Handmatig (wekelijks)

```bash
cd <fork-directory>
git fetch upstream
git merge upstream/main
# Los eventuele conflicts op
git push
```

### Geautomatiseerd (GitHub Actions)

Maak `.github/workflows/upstream-sync.yml` in elke fork:

```yaml
name: Sync upstream
on:
  schedule:
    - cron: '0 6 * * 1'  # Elke maandag 06:00 UTC
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Sync upstream
        run: |
          git remote add upstream https://github.com/<upstream-org>/<upstream-repo>.git || true
          git fetch upstream
          git merge upstream/main --no-edit || echo "::warning::Merge conflict, manual resolution needed"
          git push
```

---

## Stap 5: Na-setup verificatie

```bash
# Lijst alle repos in de org
gh repo list marqed-ai --json name,isPrivate --jq '.[] | "\(.name) (private: \(.isPrivate))"'

# Verifieer forks hebben upstream
gh api repos/marqed-ai/fork--plane --jq '.parent.full_name'

# Check dat autoforge code aanwezig is
gh api repos/marqed-ai/autoforge/commits --jq '.[0].commit.message'
```

---

## Naming Conventions

| Type | Pattern | Voorbeeld |
|------|---------|-----------|
| Eigen repo | `mq-<component>` | `mq-discover`, `mq-devEngine` |
| Fork | upstream naam behouden | `plane`, `litellm` |
| Release tag | `v{semver}` | `v1.0.0` |
| Sprint tag | `sprint/{cycle-name}` | `sprint/sprint-a-auth-teams` |

---

## Beveiliging

- Alle repos zijn **private**
- GitHub org moet 2FA verplichten: Settings → Authentication security → Require 2FA
- API keys **nooit** in repo — gebruik GitHub Secrets of `.env` (in .gitignore)
- Branch protection op `main`: require PR review, status checks

---

## Kosten

| Plan | Prijs | Wat je krijgt |
|------|-------|--------------|
| Free | $0 | Unlimited private repos, 3 collaborators, 500 MB packages, 2000 CI min/month |
| Team | $4/user/month | Code review, required reviewers, pages, 2 GB packages |

Free plan is voldoende voor de start. Upgrade naar Team wanneer er meer dan 3 developers zijn.

---

## Timing

Geschatte doorlooptijd: **30-45 minuten** (eerste keer, inclusief token setup).

Voorwaarden:
- GitHub account ingelogd
- `gh` CLI geauthenticeerd met `admin:org` scope
- Email adres voor de organisatie
