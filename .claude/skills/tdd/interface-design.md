# Designing Testable Interfaces

## Step 1: Identify the Public Interface

Before writing any test, answer:
- **Who calls this code?** (API client, React component, CLI user, another service)
- **What do they pass in?** (Parameters, request body, props)
- **What do they get back?** (Response, rendered output, side effects)
- **What can go wrong?** (Validation errors, not found, unauthorized)

## Step 2: List Testable Behaviours

Turn the feature description into a list of behaviours:

**Feature**: "User can create a todo"

| # | Behaviour | Test Type |
|---|-----------|-----------|
| 1 | POST /api/todos with valid title returns 201 + todo object | Integration |
| 2 | Created todo has completed=false by default | Integration |
| 3 | Created todo appears in GET /api/todos | Integration |
| 4 | Missing title returns 400 with validation error | Integration |
| 5 | Empty string title returns 400 | Unit (validator) |
| 6 | Title over 500 chars returns 400 | Unit (validator) |

## Step 3: Pick the Tracer Bullet

The **tracer bullet** is the ONE behaviour that proves the feature works end-to-end. It's always your first test.

For "User can create a todo": **Behaviour #1** (POST returns 201 + todo).

This test exercises: routing → validation → persistence → response formatting.

If this test passes, you know the plumbing works. All other tests are refinements.

## Step 4: Order the Remaining Behaviours

After the tracer bullet, implement in this order:
1. **Core happy path** variations (#2, #3)
2. **Validation/error handling** (#4, #5, #6)
3. **Edge cases** (concurrency, race conditions, limits)

## Interface Design Patterns

### Functions
```typescript
// Input: minimal, typed parameters
// Output: typed return value
// Errors: thrown exceptions with clear types
function createTodo(title: string): Promise<Todo>
```

### API Endpoints
```typescript
// Input: HTTP method + path + body/params
// Output: status code + response body
// Errors: status codes (400, 404, 500) + error body
POST /api/todos  { title: string }  →  201 { id, title, completed }
```

### React Components
```typescript
// Input: props
// Output: rendered elements + callbacks
// Errors: error boundaries, validation messages
interface TodoFormProps {
  onSubmit: (title: string) => void
  disabled?: boolean
}
```

## The "What Would the README Say?" Test

If you were writing documentation for this interface, what examples would you show? Those examples ARE your test cases.

```markdown
## Usage

### Create a todo
const todo = await createTodo('Buy milk')
// → { id: 1, title: 'Buy milk', completed: false }

### Handle validation
await createTodo('')
// → throws ValidationError('Title is required')
```

Each code example in the "README" becomes a test.
