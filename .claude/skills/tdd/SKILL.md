---
name: tdd
description: Red/Green/Refactor TDD workflow for coding agents. Use this skill when implementing features with tdd_enabled=true. Guides agents through writing one failing test at a time, making it pass with minimal code, then refactoring. Based on Simon Willison's agentic TDD and Matt Pocock's TDD skill.
---

# Test-Driven Development Skill

This skill guides coding agents through the Red/Green/Refactor cycle when implementing features. The core principle: **one test at a time**, never batch-write tests.

## The Red/Green/Refactor Cycle

```
┌─────────────────────────────────────────┐
│  1. RED: Write ONE failing test         │
│     → Run it → Confirm it FAILS         │
│                                         │
│  2. GREEN: Write MINIMAL code to pass   │
│     → Run it → Confirm it PASSES        │
│                                         │
│  3. REFACTOR: Clean up (tests green)    │
│     → Run it → Confirm STILL green      │
│                                         │
│  4. REPEAT from step 1                  │
└─────────────────────────────────────────┘
```

## Before Writing Any Test

1. **Recall test framework** from session memory (`memory_recall` with key="test-framework")
2. **Identify the public interface** - what does the user interact with?
3. **List testable behaviours** (NOT implementation details)
4. **Pick the tracer bullet** - the ONE behaviour that proves the feature works end-to-end

## Writing Tests: The Rules

### DO
- Write ONE test, run it, see it fail, THEN write code
- Test **behaviour** ("user can create a todo") not **implementation** ("insertTodo calls db.insert")
- Use descriptive test names: `test_creating_todo_returns_201_with_id`
- Test the public API/interface, not internal functions
- Keep tests independent - no shared mutable state
- Use `beforeEach`/`setUp` for fresh fixtures per test

### DON'T
- Never write more than one test before making it pass
- Never test private methods or internal state
- Never write tests that depend on execution order
- Never mock what you don't own (wrap external deps first)
- Never write a test that can't fail (tautological tests)

## The Integration-First Approach

Prefer **integration-style tests** that test real behaviour:

```
GOOD: Test that POST /api/todos creates a todo and GET /api/todos returns it
BAD:  Test that TodoService.create() calls repository.save()
```

Unit tests are for **complex logic** (validation, calculations, state machines).
Integration tests are for **features** (API endpoints, user workflows, data persistence).

## Knowing When You're Done

A feature is complete when:
1. All testable behaviours from your list have passing tests
2. Edge cases are covered (invalid input, empty state, error paths)
3. The full test suite passes (no regressions)
4. You can explain what each test proves about the feature

## Related Guides

- [tests.md](./tests.md) - Good vs bad tests, integration approach
- [mocking.md](./mocking.md) - When and how to mock
- [deep-modules.md](./deep-modules.md) - Small interface, deep implementation
- [interface-design.md](./interface-design.md) - Designing testable interfaces
- [refactoring.md](./refactoring.md) - Refactor candidates after green
