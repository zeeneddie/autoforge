# Mocking Strategy

## When to Mock

Mock at the **boundary** of your system, not inside it.

### DO Mock
- **External APIs** (payment providers, email services, third-party APIs)
- **System resources** (filesystem, clock, random number generators)
- **Slow operations** (network requests, heavy computations in test)

### DON'T Mock
- **Your own code** (services, repositories, utils) - test the real thing
- **The database** in integration tests - use a test database
- **Framework internals** (Express middleware chain, React rendering)

## The Rule: Don't Mock What You Don't Own

If you don't control the interface, wrap it first:

```typescript
// BAD: Mocking Stripe directly
vi.mock('stripe', () => ({ charges: { create: vi.fn() } }))

// GOOD: Wrap in your own interface, mock that
// src/payments.ts
export interface PaymentGateway {
  charge(amount: number, currency: string): Promise<{ id: string }>
}

export class StripeGateway implements PaymentGateway {
  async charge(amount: number, currency: string) {
    return stripe.charges.create({ amount, currency })
  }
}

// test: Mock YOUR interface
const mockPayments: PaymentGateway = {
  charge: vi.fn().mockResolvedValue({ id: 'ch_test_123' })
}
```

## Dependency Injection for Testability

Pass dependencies in, don't import them:

```typescript
// BAD: Hard-coded dependency
import { db } from './database'

export function createTodo(title: string) {
  return db.insert('todos', { title, completed: false })
}

// GOOD: Injectable dependency
export function createTodo(db: Database, title: string) {
  return db.insert('todos', { title, completed: false })
}

// In production: createTodo(realDb, title)
// In test: createTodo(testDb, title)
```

## Test Database Strategy

For integration tests, use a real database with isolation:

```typescript
// Per-test isolation with transactions
let db: Database

beforeEach(async () => {
  db = await createTestDatabase()  // Fresh DB or start transaction
})

afterEach(async () => {
  await db.cleanup()  // Rollback transaction or drop test DB
})
```

**SQLite**: Use `:memory:` databases for fast isolated tests.
**PostgreSQL**: Use transactions that rollback after each test.

## Mock Data in Tests vs Production

- **Test files** (`__tests__/`, `tests/`, `*.test.*`): Mock/fixture data is EXPECTED and CORRECT
- **Production code** (`src/`, `lib/`): Mock/hardcoded data is PROHIBITED

This distinction is critical. The agent must never confuse test fixtures with production mock data.
