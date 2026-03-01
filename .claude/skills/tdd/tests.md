# Writing Good Tests

## Good Tests vs Bad Tests

### Good: Tests behaviour
```typescript
test('creating a todo returns it with completed=false', async () => {
  const response = await fetch('/api/todos', {
    method: 'POST',
    body: JSON.stringify({ title: 'Buy milk' }),
  })
  const todo = await response.json()

  expect(response.status).toBe(201)
  expect(todo.title).toBe('Buy milk')
  expect(todo.completed).toBe(false)
  expect(todo.id).toBeDefined()
})
```

### Bad: Tests implementation
```typescript
// DON'T: Tests HOW, not WHAT
test('create todo calls database insert', async () => {
  const dbSpy = vi.spyOn(database, 'insert')
  await todoService.create({ title: 'Buy milk' })
  expect(dbSpy).toHaveBeenCalledWith('todos', { title: 'Buy milk', completed: false })
})
```

## The Integration-First Hierarchy

1. **Integration tests** - test feature behaviour through the public API
2. **Unit tests** - test complex pure logic (validation, calculations, transformations)
3. **Browser tests** - test visual/interactive behaviour (only when unit/integration can't cover it)

Most features need 70% integration, 20% unit, 10% browser (if any).

## Test Structure: Arrange-Act-Assert

Every test follows this pattern:

```typescript
test('descriptive name of the behaviour', async () => {
  // Arrange: Set up the preconditions
  const user = await createTestUser({ name: 'Alice' })

  // Act: Perform the action under test
  const response = await fetch(`/api/users/${user.id}`)
  const result = await response.json()

  // Assert: Verify the expected outcome
  expect(result.name).toBe('Alice')
})
```

## One Assertion Theme Per Test

A test should verify ONE logical behaviour. Multiple `expect` calls are fine if they verify aspects of the same behaviour:

```typescript
// GOOD: Multiple asserts about the same behaviour
test('new user has correct defaults', () => {
  const user = createUser({ name: 'Alice' })
  expect(user.name).toBe('Alice')
  expect(user.role).toBe('viewer')       // default role
  expect(user.createdAt).toBeDefined()    // timestamp set
})

// BAD: Testing unrelated behaviours
test('user operations', () => {
  const user = createUser({ name: 'Alice' })
  expect(user.name).toBe('Alice')         // creation
  user.updateRole('admin')
  expect(user.role).toBe('admin')         // update - separate test!
})
```

## Edge Cases to Always Cover

For every feature, test these categories:

| Category | Examples |
|----------|----------|
| **Happy path** | Valid input produces expected output |
| **Invalid input** | Missing required fields, wrong types, empty strings |
| **Empty state** | No items yet, first-time use |
| **Boundary values** | Zero, one, max length, negative numbers |
| **Error paths** | Network failure, not found, unauthorized |
| **Idempotency** | Same action twice produces same result |

## Avoiding Flaky Tests

- Never depend on timing (`setTimeout`, `sleep`)
- Never depend on test execution order
- Use unique test data per test (timestamps, UUIDs)
- Clean up in `beforeEach`, not `afterEach`
- For async: always `await` or return the promise
- For dates: freeze time or use relative assertions (`expect(date).toBeCloseTo(now, 1000)`)
