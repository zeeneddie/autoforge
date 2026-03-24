"""
Prompt Loading Utilities
========================

Functions for loading prompt templates with project-specific support.

Fallback chain:
1. Project-specific: {project_dir}/prompts/{name}.md
2. Base template: .claude/templates/{name}.template.md
"""

import json
import re
import shutil
from pathlib import Path

# Base templates location (generic templates)
TEMPLATES_DIR = Path(__file__).parent / ".claude" / "templates"


def get_project_prompts_dir(project_dir: Path) -> Path:
    """Get the prompts directory for a specific project."""
    from devengine_paths import get_prompts_dir
    return get_prompts_dir(project_dir)


def load_prompt(name: str, project_dir: Path | None = None) -> str:
    """
    Load a prompt template with fallback chain.

    Fallback order:
    1. Project-specific: {project_dir}/prompts/{name}.md
    2. Base template: .claude/templates/{name}.template.md

    Args:
        name: The prompt name (without extension), e.g., "initializer_prompt"
        project_dir: Optional project directory for project-specific prompts

    Returns:
        The prompt content as a string

    Raises:
        FileNotFoundError: If prompt not found in any location
    """
    # 1. Try project-specific first
    if project_dir:
        project_prompts = get_project_prompts_dir(project_dir)
        project_path = project_prompts / f"{name}.md"
        if project_path.exists():
            try:
                return project_path.read_text(encoding="utf-8")
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not read {project_path}: {e}")

    # 2. Try base template
    template_path = TEMPLATES_DIR / f"{name}.template.md"
    if template_path.exists():
        try:
            return template_path.read_text(encoding="utf-8")
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not read {template_path}: {e}")

    raise FileNotFoundError(
        f"Prompt '{name}' not found in:\n"
        f"  - Project: {project_dir / 'prompts' if project_dir else 'N/A'}\n"
        f"  - Templates: {TEMPLATES_DIR}"
    )


def get_architect_prompt(project_dir: Path | None = None, tdd_mode: bool = False) -> str:
    """Load the architect agent prompt (project-specific if available).

    Args:
        project_dir: Optional project directory for project-specific prompts
        tdd_mode: If True, inject TDD testing strategy section
    """
    prompt = load_prompt("architect_prompt", project_dir)
    if tdd_mode:
        prompt = _inject_architect_tdd_section(prompt)
    return prompt


def get_initializer_prompt(project_dir: Path | None = None, tdd_mode: bool = False) -> str:
    """Load the initializer prompt (project-specific if available).

    Args:
        project_dir: Optional project directory for project-specific prompts
        tdd_mode: If True, inject TDD infrastructure feature and test hints
    """
    prompt = load_prompt("initializer_prompt", project_dir)
    if tdd_mode:
        prompt = _inject_initializer_tdd_section(prompt)
    return prompt


def _strip_browser_testing_sections(prompt: str) -> str:
    """Strip browser automation and Playwright testing instructions from prompt.

    Used in YOLO mode where browser testing is skipped entirely. Replaces
    browser-related sections with a brief YOLO-mode note while preserving
    all non-testing instructions (implementation, git, progress notes, etc.).

    Args:
        prompt: The full coding prompt text.

    Returns:
        The prompt with browser testing sections replaced by YOLO guidance.
    """
    original_prompt = prompt

    # Replace STEP 5 (browser automation verification) with YOLO note
    prompt = re.sub(
        r"### STEP 5: VERIFY WITH BROWSER AUTOMATION.*?(?=### STEP 5\.5:)",
        "### STEP 5: VERIFY FEATURE (YOLO MODE)\n\n"
        "**YOLO mode is active.** Skip browser automation testing. "
        "Instead, verify your feature works by ensuring:\n"
        "- Code compiles without errors (lint and type-check pass)\n"
        "- Server starts without errors after your changes\n"
        "- No obvious runtime errors in server logs\n\n",
        prompt,
        flags=re.DOTALL,
    )

    # Replace the screenshots-only marking rule with YOLO-appropriate wording
    prompt = prompt.replace(
        "**ONLY MARK A FEATURE AS PASSING AFTER VERIFICATION WITH SCREENSHOTS.**",
        "**YOLO mode: Mark a feature as passing after lint/type-check succeeds and server starts cleanly.**",
    )

    # Replace the BROWSER AUTOMATION reference section
    prompt = re.sub(
        r"## BROWSER AUTOMATION\n\n.*?(?=---)",
        "## VERIFICATION (YOLO MODE)\n\n"
        "Browser automation is disabled in YOLO mode. "
        "Verify features by running lint, type-check, and confirming the dev server starts without errors.\n\n",
        prompt,
        flags=re.DOTALL,
    )

    # In STEP 4, replace browser automation reference with YOLO guidance
    prompt = prompt.replace(
        "2. Test manually using browser automation (see Step 5)",
        "2. Verify code compiles (lint and type-check pass)",
    )

    if prompt == original_prompt:
        print("[YOLO] Warning: No browser testing sections found to strip. "
              "Project-specific prompt may need manual YOLO adaptation.")

    return prompt


def _inject_tdd_sections(prompt: str) -> str:
    """Inject TDD Red/Green/Refactor sections into the coding prompt.

    Adds TDD guidance between Step 3 (Get Feature) and Step 4 (Implement).
    The injected sections instruct the agent to follow the one-test-at-a-time
    discipline with explicit red/green verification.

    Args:
        prompt: The full coding prompt text.

    Returns:
        The prompt with TDD sections injected.
    """
    tdd_section = """
### STEP 3.5: PLAN THE INTERFACE (TDD MODE)

**TDD mode is active.** Before writing any code, plan your approach:

1. **Recall test framework**: Use `memory_recall` with key="test-framework" to get the project's testing setup
2. **Identify the public interface**: What does the user/consumer interact with? (API endpoints, component props, function signatures)
3. **List testable behaviours**: Write down 3-7 behaviours this feature should exhibit. Focus on WHAT, not HOW:
   - GOOD: "POST /api/todos with valid title returns 201 with todo object"
   - BAD: "TodoService calls database.insert with correct parameters"
4. **Pick the tracer bullet**: Which ONE behaviour proves the feature works end-to-end? This is your first test.

### STEP 4: RED/GREEN/REFACTOR CYCLE (TDD MODE)

**CRITICAL: ONE test at a time. Never write multiple tests before making them pass.**

For each behaviour in your list:

#### 4a. RED - Write ONE Failing Test
- Write a single test that describes the expected behaviour
- Run the test suite: it MUST FAIL (red)
- If it passes without new code, the test is useless - rewrite it
- Confirm the failure message makes sense (it should describe what's missing)

#### 4b. GREEN - Write MINIMAL Implementation
- Write the MINIMUM code needed to make the failing test pass
- Do NOT write more than what the test requires
- Run the test suite: it MUST PASS (green)
- All previous tests must ALSO still pass (no regressions)

#### 4c. REFACTOR - Clean Up (Tests Stay Green)
- Look for duplication, unclear naming, or overly complex code
- Refactor ONLY if there's a clear improvement
- Run the test suite after refactoring: MUST still be green
- Skip this step if the code is already clean

#### 4d. REPEAT
- Go back to 4a with the next behaviour from your list
- Continue until all behaviours have passing tests

**MOCK DATA CLARIFICATION (TDD MODE):**
- In TEST files (`__tests__/`, `tests/`, `*.test.*`, `*.spec.*`): test fixtures and mock data are EXPECTED and CORRECT
- In PRODUCTION code (`src/`, `lib/`, `app/`): mock/hardcoded data remains STRICTLY PROHIBITED

### STEP 4.5: RUN FULL TEST SUITE (TDD MODE)

After completing all behaviours for this feature:
1. Run the COMPLETE test suite (not just this feature's tests)
2. ALL tests must pass (verify no regressions from other features)
3. If other features' tests break, fix the regressions before proceeding

### STEP 4.6: RECORD TEST RESULTS (TDD MODE)

After all tests pass for this feature, record the test metadata:

```
feature_record_test(
    feature_id=<your feature id>,
    test_file_path="src/__tests__/yourFeature.test.ts",
    test_count=<number of test cases>,
    passed=true,
    output_snippet="<first lines of test output>"
)
```

This is MANDATORY before calling feature_mark_passing. Without it, test tracking is incomplete.

"""

    # Replace STEP 4 (implementation step) with TDD cycle
    # Match from STEP 4 header up to STEP 5 header (replacing the original implementation guidance)
    step4_to_step5 = re.compile(
        r"### STEP 4: IMPLEMENT.*?(?=### STEP 5:)",
        re.DOTALL | re.IGNORECASE,
    )
    match = step4_to_step5.search(prompt)
    if match:
        prompt = prompt[:match.start()] + tdd_section + prompt[match.start() + len(match.group()):]
    else:
        # Fallback: try to find just STEP 4 header
        step4_pattern = re.compile(r"(### STEP 4: IMPLEMENT)", re.IGNORECASE)
        match2 = step4_pattern.search(prompt)
        if match2:
            prompt = prompt[:match2.start()] + tdd_section + prompt[match2.end():]
        else:
            print("[TDD] Warning: Could not find STEP 4 marker. Appending TDD sections at end.")
            prompt += "\n" + tdd_section

    # Replace the feature marking rule to include test evidence
    prompt = prompt.replace(
        "**ONLY MARK A FEATURE AS PASSING AFTER VERIFICATION WITH SCREENSHOTS.**",
        "**TDD mode: Mark a feature as passing ONLY after all tests pass (red→green cycle completed for every behaviour).**",
    )
    prompt = prompt.replace(
        "**YOLO mode: Mark a feature as passing after lint/type-check succeeds and server starts cleanly.**",
        "**TDD mode: Mark a feature as passing ONLY after all tests pass (red→green cycle completed for every behaviour).**",
    )

    return prompt


def _inject_architect_tdd_section(prompt: str) -> str:
    """Inject TDD testing strategy section into the architect prompt.

    Adds a section for the architect to decide on test framework and strategy,
    storing the decision via memory_store for coding agents to recall.

    Args:
        prompt: The architect prompt text.

    Returns:
        The prompt with TDD architecture section injected.
    """
    tdd_architecture = """

### 3.7: Testing Strategy (TDD MODE)

**TDD mode is active.** The coding agents will follow Red/Green/Refactor. You must decide:

1. **Test Runner**: Choose the appropriate test framework for this project:
   - JavaScript/TypeScript: Vitest (preferred), Jest, or built-in Node test runner
   - Python: pytest (preferred), unittest
   - Other: framework-appropriate test runner
2. **Test File Location**: Define the convention:
   - Co-located: `src/components/Button.test.tsx` (next to source)
   - Separate: `tests/components/Button.test.tsx` (mirror structure)
   - Python: `tests/test_*.py` (standard pytest discovery)
3. **Test Commands**: The exact commands to run tests:
   - Single test file: e.g., `npx vitest run src/api/todos.test.ts`
   - Full suite: e.g., `npx vitest run`
4. **Mocking Strategy**: When to mock vs use real implementations
5. **Test Database**: For integration tests, how to manage test data (in-memory SQLite, test fixtures, etc.)

**Store your decisions using `memory_store`:**
```
memory_store(key="test-framework", category="architecture", value="<your testing strategy as structured text>")
```

"""

    # Try to inject after section 3.6 or before STEP 4
    step4_marker = re.search(r"(## STEP 4:|### STEP 4:)", prompt, re.IGNORECASE)
    section_36 = re.search(r"(### 3\.6[:\s])", prompt)

    if section_36:
        # Find the end of section 3.6 (next section header or step)
        next_section = re.search(r"\n(##[# ])", prompt[section_36.end():])
        if next_section:
            insert_pos = section_36.end() + next_section.start()
        else:
            insert_pos = len(prompt)
        prompt = prompt[:insert_pos] + tdd_architecture + prompt[insert_pos:]
    elif step4_marker:
        prompt = prompt[:step4_marker.start()] + tdd_architecture + "\n" + prompt[step4_marker.start():]
    else:
        prompt += tdd_architecture

    return prompt


def _inject_initializer_tdd_section(prompt: str) -> str:
    """Inject TDD infrastructure feature and test hints into the initializer prompt.

    Adds guidance for creating a test framework setup feature and hints
    for test-friendly feature descriptions.

    Args:
        prompt: The initializer prompt text.

    Returns:
        The prompt with TDD initializer guidance injected.
    """
    tdd_init_section = """

## TDD MODE: ADDITIONAL INFRASTRUCTURE FEATURE

**TDD mode is active.** Add ONE additional infrastructure feature at index 5:

**Feature 5: Test Framework Setup**
- Name: "Test framework configured and passing"
- Category: "Infrastructure"
- Description: "Install and configure the project's test framework. Create a sample test that runs and passes. Verify the test command works from the command line."
- Steps: ["Install test framework dependencies", "Create test configuration file", "Write one sample test (e.g., 1+1=2)", "Run tests and verify they pass", "Document the test command in README or CLAUDE.md"]
- Priority: 1 (required before any feature implementation)
- Dependencies: Features 0-4 (all other infrastructure)

**TEST STRATEGY HINTS PER FEATURE CATEGORY:**
When creating feature descriptions, include testability hints:
- **API/CRUD features**: "Testable via integration tests on API endpoints"
- **Form Validation**: "Testable via unit tests on validation functions"
- **Authentication/Security**: "Testable via unit tests on auth middleware and integration tests on protected routes"
- **Data Processing**: "Testable via unit tests on transformation functions"
- **Layout/Visual/CSS**: "Browser-only verification (not unit-testable)"
- **Accessibility**: "Browser-only or axe-core testing"
- **Performance**: "Benchmark testing (separate from TDD cycle)"

"""

    # Inject after the infrastructure features section
    infra_marker = re.search(
        r"(MANDATORY INFRASTRUCTURE FEATURES|Infrastructure Features|INFRASTRUCTURE)",
        prompt,
        re.IGNORECASE,
    )
    if infra_marker:
        # Find the end of the infrastructure section
        next_section = re.search(r"\n(##[# ])", prompt[infra_marker.end():])
        if next_section:
            insert_pos = infra_marker.end() + next_section.start()
        else:
            insert_pos = len(prompt)
        prompt = prompt[:insert_pos] + tdd_init_section + prompt[insert_pos:]
    else:
        # Fallback: append at the end
        prompt += tdd_init_section

    return prompt


def get_coding_prompt(project_dir: Path | None = None, yolo_mode: bool = False, tdd_mode: bool = False) -> str:
    """Load the coding agent prompt (project-specific if available).

    Args:
        project_dir: Optional project directory for project-specific prompts
        yolo_mode: If True, strip browser automation / Playwright testing
            instructions and replace with YOLO-mode guidance. This reduces
            prompt tokens since YOLO mode skips all browser testing anyway.
        tdd_mode: If True, inject TDD Red/Green/Refactor sections into the prompt.

    Returns:
        The coding prompt, optionally modified for YOLO and/or TDD mode.
    """
    prompt = load_prompt("coding_prompt", project_dir)

    if yolo_mode:
        prompt = _strip_browser_testing_sections(prompt)

    if tdd_mode:
        prompt = _inject_tdd_sections(prompt)

    return prompt


def get_review_prompt(
    project_dir: Path | None = None,
    review_feature_id: int | None = None,
) -> str:
    """Load the review agent prompt (project-specific if available).

    Args:
        project_dir: Optional project directory for project-specific prompts
        review_feature_id: If provided, the pre-assigned feature ID to review.

    Returns:
        The review prompt, with feature assignment populated.
    """
    base_prompt = load_prompt("review_prompt", project_dir)

    if review_feature_id is not None:
        header = f"""## ASSIGNED FEATURE FOR REVIEW: #{review_feature_id}

Review ONLY this feature. Use `feature_get_by_id` with ID {review_feature_id} to get details.
Then approve or reject based on your review.

---

"""
        return header + base_prompt

    return base_prompt


_STACK_INFO_FALLBACK = """\
Look for test configuration files (`vitest.config.*`, `jest.config.*`, `pytest.ini`, `pyproject.toml` with `[tool.pytest]`)
and run the full test suite before browser verification.

1. If tests exist: run them — e.g., `npx vitest run`, `python -m pytest`, `npm test`
2. If ALL tests pass: proceed to browser verification (Step 2)
3. If tests FAIL: mark failing feature(s) with `feature_mark_failing`, fix, re-run, then mark passing
4. If no automated tests: skip this step and proceed to Step 2\
"""


def _read_pkg_scripts(pkg_path: Path) -> dict[str, str]:
    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
        return data.get("scripts", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _detect_test_runner(app_dir: Path) -> str:
    """Return 'jest', 'vitest', or '' for an app directory."""
    if list(app_dir.glob("vitest.config.*")):
        return "vitest"
    if list(app_dir.glob("jest.config.*")):
        return "jest"
    # Check package.json scripts and jest config section
    pkg = app_dir / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            test_cmd = scripts.get("test", "")
            if "vitest" in test_cmd:
                return "vitest"
            if "jest" in test_cmd or "jest" in data:
                return "jest"
        except (json.JSONDecodeError, OSError):
            pass
    return ""


def _detect_turborepo_stack(project_dir: Path) -> str:
    """Generate test commands for a Turborepo monorepo."""
    apps_dir = project_dir / "apps"
    if not apps_dir.is_dir():
        return _STACK_INFO_FALLBACK

    apps_with_tests: list[tuple[str, str]] = []  # (app_name, runner)
    has_typecheck = False

    for app_dir in sorted(apps_dir.iterdir()):
        if not app_dir.is_dir():
            continue
        scripts = _read_pkg_scripts(app_dir / "package.json")
        if "test" not in scripts:
            continue
        runner = _detect_test_runner(app_dir)
        apps_with_tests.append((app_dir.name, runner))
        if "check-types" in scripts or "type-check" in scripts:
            has_typecheck = True

    if not apps_with_tests:
        return _STACK_INFO_FALLBACK

    app_names = " + ".join(f"{n} ({r})" if r else n for n, r in apps_with_tests)
    lines = [f"**Turborepo project detected: {app_names}**", "", "Run before browser verification:", "", "```bash"]
    for app_name, runner in apps_with_tests:
        runner_label = f"({runner})" if runner else ""
        lines.append(f"# {app_name} {runner_label}".rstrip())
        lines.append(f"npx turbo run test --filter={app_name} -- --passWithNoTests")
        lines.append("")
    if has_typecheck:
        lines.append("# TypeScript check")
        lines.append("npx turbo run check-types")
        lines.append("")
    lines.append("```")
    lines.append("")

    # Tech-specific anti-mock hints
    if (project_dir / "supabase").is_dir():
        lines.append("**Auth (Supabase):** Use real Supabase test tenant JWT. No mocks of auth middleware.")
    if any((apps_dir / app / "src" / "prisma").is_dir() for app, _ in apps_with_tests):
        lines.append("**Database (Prisma):** Use real test database. No mocks of Prisma client.")

    lines.append("")
    lines.append(
        "If tests FAIL: mark feature(s) with `feature_mark_failing`, "
        "investigate, fix, re-run, then mark passing."
    )
    return "\n".join(lines)


def _detect_python_stack(project_dir: Path) -> str:
    """Generate pytest command for a Python project."""
    lines = ["**Python project detected**", "", "Run before browser verification:", "", "```bash"]
    if (project_dir / "Makefile").exists():
        lines.append("make test  # or: python -m pytest")
    else:
        lines.append("python -m pytest")
    lines.append("```")
    lines.append("")
    lines.append(
        "If tests FAIL: mark feature(s) with `feature_mark_failing`, "
        "investigate, fix, re-run, then mark passing."
    )
    return "\n".join(lines)


def _detect_node_stack(project_dir: Path) -> str:
    """Generate test command for a plain Node.js project."""
    scripts = _read_pkg_scripts(project_dir / "package.json")
    if "test" not in scripts:
        return _STACK_INFO_FALLBACK

    test_cmd = scripts["test"]
    pm = "pnpm" if (project_dir / "pnpm-lock.yaml").exists() else "npm"
    runner = _detect_test_runner(project_dir)
    label = f"({runner})" if runner else ""

    lines = [f"**Node.js project detected {label}**".rstrip(), "", "Run before browser verification:", "", "```bash"]
    if "vitest" in test_cmd:
        lines.append(f"{pm} run test  # vitest run")
    elif "jest" in test_cmd:
        lines.append(f"{pm} run test  # jest --passWithNoTests")
    else:
        lines.append(f"{pm} run test")
    lines.append("```")
    lines.append("")
    lines.append(
        "If tests FAIL: mark feature(s) with `feature_mark_failing`, "
        "investigate, fix, re-run, then mark passing."
    )
    return "\n".join(lines)


def _detect_stack_info(project_dir: Path | None) -> str:
    """Auto-detect test stack and return formatted test instructions.

    Supports: Turborepo monorepos, Python (pytest), plain Node.js (Jest/Vitest).
    Falls back to generic guidance when nothing is detected.
    """
    if project_dir is None or not project_dir.is_dir():
        return _STACK_INFO_FALLBACK

    # Turborepo
    if (project_dir / "turbo.json").exists():
        return _detect_turborepo_stack(project_dir)

    # Python
    if (project_dir / "pytest.ini").exists():
        return _detect_python_stack(project_dir)
    pyproject = project_dir / "pyproject.toml"
    if pyproject.exists() and "[tool.pytest" in pyproject.read_text(encoding="utf-8", errors="ignore"):
        return _detect_python_stack(project_dir)

    # Plain Node.js
    if (project_dir / "package.json").exists():
        return _detect_node_stack(project_dir)

    return _STACK_INFO_FALLBACK


def get_story_planner_prompt(feature_id: int, project_dir: Path | None = None) -> str:
    """Return the story planner prompt with FEATURE_ID injected."""
    base = load_prompt("story_planner_prompt", project_dir)
    return base.replace("{{FEATURE_ID}}", str(feature_id))


def get_testing_prompt(
    project_dir: Path | None = None,
    testing_feature_id: int | None = None,
    testing_feature_ids: list[int] | None = None,
) -> str:
    """Load the testing agent prompt (project-specific if available).

    Supports both single-feature and multi-feature testing modes. When
    testing_feature_ids is provided, the template's {{TESTING_FEATURE_IDS}}
    placeholder is replaced with the comma-separated list. Falls back to
    the legacy single-feature header when only testing_feature_id is given.

    Args:
        project_dir: Optional project directory for project-specific prompts
        testing_feature_id: If provided, the pre-assigned feature ID to test (legacy single mode).
        testing_feature_ids: If provided, a list of feature IDs to test (batch mode).
            Takes precedence over testing_feature_id when both are set.

    Returns:
        The testing prompt, with feature assignment instructions populated.
    """
    base_prompt = load_prompt("testing_prompt", project_dir)

    # Inject auto-detected stack info (test commands for this project)
    stack_info = _detect_stack_info(project_dir)
    base_prompt = base_prompt.replace("{{PROJECT_STACK_INFO}}", stack_info)

    # Batch mode: replace the {{TESTING_FEATURE_IDS}} placeholder in the template
    if testing_feature_ids is not None and len(testing_feature_ids) > 0:
        ids_str = ", ".join(str(fid) for fid in testing_feature_ids)
        return base_prompt.replace("{{TESTING_FEATURE_IDS}}", ids_str)

    # Legacy single-feature mode: replace placeholder
    if testing_feature_id is not None:
        return base_prompt.replace("{{TESTING_FEATURE_IDS}}", str(testing_feature_id))

    # No feature assignment -- return template with placeholder cleared
    return base_prompt.replace("{{TESTING_FEATURE_IDS}}", "(none assigned)")


def get_single_feature_prompt(
    feature_id: int,
    project_dir: Path | None = None,
    yolo_mode: bool = False,
    tdd_mode: bool = False,
) -> str:
    """Prepend single-feature assignment header to base coding prompt.

    Used in parallel mode to assign a specific feature to an agent.
    The base prompt already contains the full workflow - this just
    identifies which feature to work on.

    Args:
        feature_id: The specific feature ID to work on
        project_dir: Optional project directory for project-specific prompts
        yolo_mode: If True, strip browser testing instructions from the base
            coding prompt for reduced token usage in YOLO mode.
        tdd_mode: If True, inject TDD Red/Green/Refactor sections.

    Returns:
        The prompt with single-feature header prepended
    """
    base_prompt = get_coding_prompt(project_dir, yolo_mode=yolo_mode, tdd_mode=tdd_mode)

    # Minimal header - the base prompt already contains the full workflow
    single_feature_header = f"""## ASSIGNED FEATURE: #{feature_id}

Work ONLY on this feature. Other agents are handling other features.
Use `feature_claim_and_get` with ID {feature_id} to claim it and get details.
If blocked, use `feature_skip` and document the blocker.

---

"""
    return single_feature_header + base_prompt


def get_batch_feature_prompt(
    feature_ids: list[int],
    project_dir: Path | None = None,
    yolo_mode: bool = False,
    tdd_mode: bool = False,
) -> str:
    """Prepend batch-feature assignment header to base coding prompt.

    Used in parallel mode to assign multiple features to an agent.
    Features should be implemented sequentially in the given order.

    Args:
        feature_ids: List of feature IDs to implement in order
        project_dir: Optional project directory for project-specific prompts
        yolo_mode: If True, strip browser testing instructions from the base prompt
        tdd_mode: If True, inject TDD Red/Green/Refactor sections.

    Returns:
        The prompt with batch-feature header prepended
    """
    base_prompt = get_coding_prompt(project_dir, yolo_mode=yolo_mode, tdd_mode=tdd_mode)
    ids_str = ", ".join(f"#{fid}" for fid in feature_ids)

    batch_header = f"""## ASSIGNED FEATURES (BATCH): {ids_str}

You have been assigned {len(feature_ids)} features to implement sequentially.
Process them IN ORDER: {ids_str}

### Workflow for each feature:
1. Call `feature_claim_and_get` with the feature ID to get its details
2. Implement the feature fully
3. Verify it works (browser testing if applicable)
4. Call `feature_mark_passing` to mark it complete
5. Git commit the changes
6. Move to the next feature

### Important:
- Complete each feature fully before starting the next
- Mark each feature passing individually as you go
- If blocked on a feature, use `feature_skip` and move to the next one
- Other agents are handling other features - focus only on yours

---

"""
    return batch_header + base_prompt


def get_app_spec(project_dir: Path) -> str:
    """
    Load the app spec from the project.

    Checks in order:
    1. Project prompts directory: {project_dir}/prompts/app_spec.txt
    2. Project root (legacy): {project_dir}/app_spec.txt

    Args:
        project_dir: The project directory

    Returns:
        The app spec content

    Raises:
        FileNotFoundError: If no app_spec.txt found
    """
    # Try project prompts directory first
    project_prompts = get_project_prompts_dir(project_dir)
    spec_path = project_prompts / "app_spec.txt"
    if spec_path.exists():
        try:
            return spec_path.read_text(encoding="utf-8")
        except (OSError, PermissionError) as e:
            raise FileNotFoundError(f"Could not read {spec_path}: {e}") from e

    # Fallback to legacy location in project root
    legacy_spec = project_dir / "app_spec.txt"
    if legacy_spec.exists():
        try:
            return legacy_spec.read_text(encoding="utf-8")
        except (OSError, PermissionError) as e:
            raise FileNotFoundError(f"Could not read {legacy_spec}: {e}") from e

    raise FileNotFoundError(f"No app_spec.txt found for project: {project_dir}")


def scaffold_project_prompts(project_dir: Path) -> Path:
    """
    Create the project prompts directory and copy base templates.

    This sets up a new project with template files that can be customized.

    Args:
        project_dir: The absolute path to the project directory

    Returns:
        The path to the project prompts directory
    """
    project_prompts = get_project_prompts_dir(project_dir)
    project_prompts.mkdir(parents=True, exist_ok=True)

    # Create .mq-devengine directory with .gitignore for runtime files
    from devengine_paths import ensure_devengine_dir
    devengine_dir = ensure_devengine_dir(project_dir)

    # Define template mappings: (source_template, destination_name)
    templates = [
        ("app_spec.template.txt", "app_spec.txt"),
        ("coding_prompt.template.md", "coding_prompt.md"),
        ("initializer_prompt.template.md", "initializer_prompt.md"),
        ("testing_prompt.template.md", "testing_prompt.md"),
    ]

    copied_files = []
    for template_name, dest_name in templates:
        template_path = TEMPLATES_DIR / template_name
        dest_path = project_prompts / dest_name

        # Only copy if template exists and destination doesn't
        if template_path.exists() and not dest_path.exists():
            try:
                shutil.copy(template_path, dest_path)
                copied_files.append(dest_name)
            except (OSError, PermissionError) as e:
                print(f"  Warning: Could not copy {dest_name}: {e}")

    # Copy allowed_commands.yaml template to .mq-devengine/
    examples_dir = Path(__file__).parent / "examples"
    allowed_commands_template = examples_dir / "project_allowed_commands.yaml"
    allowed_commands_dest = devengine_dir / "allowed_commands.yaml"
    if allowed_commands_template.exists() and not allowed_commands_dest.exists():
        try:
            shutil.copy(allowed_commands_template, allowed_commands_dest)
            copied_files.append(".mq-devengine/allowed_commands.yaml")
        except (OSError, PermissionError) as e:
            print(f"  Warning: Could not copy allowed_commands.yaml: {e}")

    if copied_files:
        print(f"  Created project files: {', '.join(copied_files)}")

    return project_prompts


def has_project_prompts(project_dir: Path) -> bool:
    """
    Check if a project has valid prompts set up.

    A project has valid prompts if:
    1. The prompts directory exists, AND
    2. app_spec.txt exists within it, AND
    3. app_spec.txt contains the <project_specification> tag

    Args:
        project_dir: The project directory to check

    Returns:
        True if valid project prompts exist, False otherwise
    """
    project_prompts = get_project_prompts_dir(project_dir)
    app_spec = project_prompts / "app_spec.txt"

    if not app_spec.exists():
        # Also check legacy location in project root
        legacy_spec = project_dir / "app_spec.txt"
        if legacy_spec.exists():
            try:
                content = legacy_spec.read_text(encoding="utf-8")
                return "<project_specification>" in content
            except (OSError, PermissionError):
                return False
        return False

    # Check for valid spec content
    try:
        content = app_spec.read_text(encoding="utf-8")
        return "<project_specification>" in content
    except (OSError, PermissionError):
        return False


def copy_spec_to_project(project_dir: Path) -> None:
    """
    Copy the app spec file into the project root directory for the agent to read.

    This maintains backwards compatibility - the agent expects app_spec.txt
    in the project root directory.

    The spec is sourced from: {project_dir}/prompts/app_spec.txt

    Args:
        project_dir: The project directory
    """
    spec_dest = project_dir / "app_spec.txt"

    # Don't overwrite if already exists
    if spec_dest.exists():
        return

    # Copy from project prompts directory
    project_prompts = get_project_prompts_dir(project_dir)
    project_spec = project_prompts / "app_spec.txt"
    if project_spec.exists():
        try:
            shutil.copy(project_spec, spec_dest)
            print("Copied app_spec.txt to project directory")
            return
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not copy app_spec.txt: {e}")
            return

    print("Warning: No app_spec.txt found to copy to project directory")
