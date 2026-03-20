# Sprint 7.3.1: Feature Checkpoint Tags

> Status: PLANNED
> Prioriteit: HIGH — fundament voor mq-supervisor Fase A + spec-kwaliteitscontrole
> Afhankelijkheden: Sprint 7.3 (stuck-state recovery IPC patroon)

## Dubbel doel: kwaliteits- én voortgangscontrole

De checkpoint-tags zijn meer dan alleen recovery-mechanisme. Ze zijn het fundament voor twee typen controle die mq-devEngine nu mist:

1. **Voortgangscontrole** — Pre-tag = feature gestart, post-tag = feature voltooid. mq-supervisor kan exact zien hoever het buildproces gevorderd was bij een crash, zonder de git-log te parsen.
2. **Spec-kwaliteitscontrole** — Een ontbrekende post-tag na 90 min is een signaal dat de feature te groot, te vaag, of te complex was voor de gegeven ACs. Dit stuurt terug naar de PO (spec-kwaliteit), niet alleen naar de developer (code-fout).

## Probleem 1 — Geen rollback-punt bij feature crash

mq-devEngine start features zonder git-ankerpunt. Wanneer een agent halverwege crasht, is de git-staat onbekend:
- Half-geschreven bestanden kunnen in de working tree achterblijven
- De volgende RETRY-poging begint in een vervuilde staat
- mq-supervisor (externe service) kan niet rollbacken zonder het exacte pre-build commit te kennen

## Probleem 2 — Geen objectief voortgangssignaal naar externe services

mq-supervisor en mq-cockpit kunnen niet zien of een feature gestart of voltooid is zonder de git-log te parsen. Dit is fragiel en schaalt niet:
- Git-log parsen vereist kennis van commit message formats
- Geen gegarandeerde aanwezigheid van commits (agent kan crashen voor eerste commit)
- Geen tijdstempel van wanneer de feature werd gestart

## Probleem 3 — Spec-kwaliteitsfeedback mist empirische basis

Een feature die 3x herstart zonder post-tag is een signaal dat de ACs onvoldoende zijn. Dit signaal gaat nu verloren:
- Stuck-state detectie (Sprint 7.3) triggert na 90 min — maar er is geen sprint-niveau patroon analyse
- mq-supervisor kan niet onderscheiden tussen "slechte code" en "slechte spec"
- PO heeft geen feedback of features structureel vastlopen door spec-kwaliteit

## Oplossing

Twee lightweight git tags per feature:
```
mq-cp-{feature_id}-pre    # bij claim, vóór agent start
mq-cp-{feature_id}-post   # na passes=True (succesvolle build + tests)
```

Dit maakt het volgende mogelijk:
```
Feature start → [pre-tag] → codewijzigingen → crash →
  mq-supervisor: git reset --hard mq-cp-{fid}-pre (schone staat)
                → succes → [post-tag] → bevestigt build OK
```

API endpoints voor mq-supervisor:
- `GET /api/projects/{name}/checkpoints` — leest alle mq-cp-* tags
- `POST /api/projects/{name}/rollback/{fid}` — reset naar pre-tag

Tag-patroon maakt spec-kwaliteitssignaal meetbaar via mq-supervisor Fase D:
- `pre_count` per sprint vs `post_count` per sprint = completion ratio
- Ratio < 0.5 voor 2+ features = structureel spec-kwaliteitsprobleem

## Fase 0 — worktree_manager.py: 3 nieuwe async functies

```python
async def create_feature_checkpoint(project_dir: Path, feature_id: int, phase: str) -> str:
    """Create lightweight git tag as checkpoint anchor.
    phase: 'pre' (before feature start) or 'post' (after successful build).
    Returns the tag name. Idempotent via -f flag.
    """
    tag = f"mq-cp-{feature_id}-{phase}"
    await _run_git("tag", "-f", tag, cwd=project_dir, check=False)
    return tag

def create_feature_checkpoint_sync(project_dir: Path, feature_id: int, phase: str) -> str:
    """Sync wrapper for use in synchronous orchestrator context."""
    import subprocess
    tag = f"mq-cp-{feature_id}-{phase}"
    subprocess.run(["git", "tag", "-f", tag], cwd=str(project_dir), capture_output=True)
    return tag

async def list_feature_checkpoints(project_dir: Path) -> list[dict]:
    """List all mq-cp-* tags with reflog timestamps.
    Returns: [{"feature_id": int, "phase": "pre"|"post", "tag": str, "timestamp": str}]
    """
    rc, stdout, _ = await _run_git(
        "tag", "-l", "mq-cp-*", "--sort=-creatordate",
        "--format=%(refname:short)|%(creatordate:iso)",
        cwd=project_dir, check=False,
    )
    result = []
    if rc != 0 or not stdout:
        return result
    for line in stdout.splitlines():
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        tag, timestamp = parts
        # Parse tag: mq-cp-{feature_id}-{phase}
        segments = tag.split("-")
        if len(segments) >= 4 and segments[0] == "mq" and segments[1] == "cp":
            try:
                feature_id = int(segments[2])
                phase = segments[3]
                result.append({
                    "feature_id": feature_id,
                    "phase": phase,
                    "tag": tag,
                    "timestamp": timestamp,
                })
            except ValueError:
                continue
    return result

async def rollback_to_checkpoint(project_dir: Path, feature_id: int) -> bool:
    """Hard reset to mq-cp-{feature_id}-pre tag. Returns False if tag absent."""
    tag = f"mq-cp-{feature_id}-pre"
    rc, _, _ = await _run_git("reset", "--hard", tag, cwd=project_dir, check=False)
    return rc == 0
```

Toevoegen NA de `_run_git` functie definitie en vóór de `is_git_repo` functie.

## Fase 1 — parallel_orchestrator.py: 2 checkpoint aanroepen

**Pre-tag:** Na `feature.in_progress = True` en `session.commit()` (omstreeks line 1483-1484):
```python
# Checkpoint: mark feature start in git (for mq-supervisor rollback + progress tracking)
import worktree_manager as _wm
_wm.create_feature_checkpoint_sync(Path(project_dir), feature.id, "pre")
```

**Post-tag:** In de completion handler, na het vaststellen dat `feat.passes == True` per feature. Zoek naar de loop `for fid in all_feature_ids:` die `feat.passes` controleert en voeg tag toe:
```python
# Checkpoint: mark feature completion in git
if feat.passes:
    import worktree_manager as _wm
    _wm.create_feature_checkpoint_sync(Path(project_dir), fid, "post")
```

## Fase 2 — server/routers/projects.py: 2 nieuwe endpoints

```python
@router.get("/{name}/checkpoints")
async def get_feature_checkpoints(name: str) -> list[dict]:
    """List all feature checkpoint tags for a project.
    Used by mq-supervisor to determine feature progress and stuck detection.
    Returns: [{"feature_id": int, "phase": "pre"|"post", "tag": str, "timestamp": str}]
    """
    _init_imports()
    (_, _, get_project_path, _, _, _, _) = _get_registry_functions()
    name = validate_project_name(name)
    project_dir = get_project_path(name)
    if not project_dir:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    import sys
    root = Path(__file__).parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import worktree_manager
    checkpoints = await worktree_manager.list_feature_checkpoints(project_dir)
    # Group by feature_id: merge pre/post into one record per feature
    grouped: dict[int, dict] = {}
    for cp in checkpoints:
        fid = cp["feature_id"]
        if fid not in grouped:
            grouped[fid] = {"feature_id": fid, "pre": False, "post": False,
                            "pre_ts": None, "post_ts": None}
        if cp["phase"] == "pre":
            grouped[fid]["pre"] = True
            grouped[fid]["pre_ts"] = cp["timestamp"]
        elif cp["phase"] == "post":
            grouped[fid]["post"] = True
            grouped[fid]["post_ts"] = cp["timestamp"]
    return list(grouped.values())


@router.post("/{name}/rollback/{feature_id}")
async def rollback_feature(name: str, feature_id: int) -> dict:
    """Rollback a feature to its pre-checkpoint git state.
    Blocked if feature is currently in_progress (returns 409 Conflict).
    Used by mq-supervisor RETRY strategy.
    """
    _init_imports()
    (_, _, get_project_path, _, _, _, _) = _get_registry_functions()
    name = validate_project_name(name)
    project_dir = get_project_path(name)
    if not project_dir:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found")

    # Check that feature is not currently in_progress
    import sys
    root = Path(__file__).parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from api.database import Feature, get_db_path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    db_path = get_db_path(project_dir)
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        feature = session.query(Feature).filter(Feature.id == feature_id).first()
        if not feature:
            raise HTTPException(status_code=404, detail=f"Feature {feature_id} not found")
        if feature.in_progress:
            raise HTTPException(status_code=409, detail=f"Feature {feature_id} is currently in_progress — cannot rollback")
    finally:
        session.close()

    import worktree_manager
    success = await worktree_manager.rollback_to_checkpoint(project_dir, feature_id)
    if not success:
        raise HTTPException(status_code=404,
            detail=f"Checkpoint mq-cp-{feature_id}-pre not found — cannot rollback")
    return {"success": True, "feature_id": feature_id,
            "message": f"Rolled back to mq-cp-{feature_id}-pre"}
```

## Config
- `stuck_timeout_min`: 90 min (configurable in mq-supervisor)
- Tags zijn idempotent: `-f` flag overschrijft bestaande tag
- Tags leven in git — geen DB-migratie nodig

## Verificatie

1. `git tag -l "mq-cp-*"` → pre-tags verschijnen na feature claim in orchestrator
2. `git tag -l "mq-cp-*"` → post-tags verschijnen na passes=True
3. `GET /api/projects/{name}/checkpoints` → JSON met pre/post per feature, inclusief timestamps
4. `POST /api/projects/{name}/rollback/{id}` → git log toont pre-tag commit
5. Rollback met `in_progress=True` feature → 409 Conflict
6. Bestaande pipeline werkt identiek — tags zijn additioneel

## Gewijzigde bestanden

| Bestand | Actie |
|---------|-------|
| `worktree_manager.py` | +4 functies: `create_feature_checkpoint`, `create_feature_checkpoint_sync`, `list_feature_checkpoints`, `rollback_to_checkpoint` |
| `parallel_orchestrator.py` | +2 checkpoint calls: pre bij claim, post bij passes=True |
| `server/routers/projects.py` | +2 endpoints: GET /checkpoints, POST /rollback/{fid} |
