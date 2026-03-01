# Refactoring After Green

## When to Refactor

Refactor ONLY after a test goes green. Never refactor while a test is red.

The refactor phase answers: "The code works. Can I make it clearer?"

## Refactor Candidates

After each green test, check for these patterns:

### 1. Duplication
```typescript
// BEFORE: Duplicated validation
function createTodo(title: string) {
  if (!title || title.trim() === '') throw new Error('Title required')
  // ...
}
function updateTodo(id: number, title: string) {
  if (!title || title.trim() === '') throw new Error('Title required')
  // ...
}

// AFTER: Extract shared validation
function validateTitle(title: string): string {
  if (!title || title.trim() === '') throw new Error('Title required')
  return title.trim()
}
```

### 2. Long Functions
If a function does more than one thing, extract helper functions. But only if you have TWO or more callers or the function exceeds ~20 lines.

### 3. Magic Values
```typescript
// BEFORE
if (title.length > 500) throw new Error('Too long')

// AFTER
const MAX_TITLE_LENGTH = 500
if (title.length > MAX_TITLE_LENGTH) throw new Error(`Title exceeds ${MAX_TITLE_LENGTH} characters`)
```

### 4. Naming
Can a reader understand the code without comments? Rename unclear variables, functions, and types.

## What NOT to Refactor

- Don't refactor code you didn't just write (out of scope)
- Don't add abstraction layers for single-use code
- Don't optimize for performance without evidence
- Don't change the public interface (that would require new tests)

## The Refactor Safety Net

After every refactor:
1. Run the test suite
2. ALL tests must still pass
3. If a test fails, your refactor changed behaviour - undo it

```
GREEN → Refactor → Run tests → Still GREEN? → Continue
                              → RED? → Undo refactor
```

## When to Skip Refactoring

It's okay to skip the refactor phase when:
- The code is already clean (common for simple behaviours)
- You're implementing the first test (nothing to refactor yet)
- The next behaviour will naturally clean up the current code

The refactor phase is the weakest for AI agents. If the code is readable and the tests pass, moving to the next RED phase is perfectly acceptable.
