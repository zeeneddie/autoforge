# Deep Modules: Small Interface, Deep Implementation

## The Principle

A well-designed module has a **small, simple interface** that hides a **deep, complex implementation**. This is the key to testable code.

```
SHALLOW MODULE (bad):        DEEP MODULE (good):
┌──────────────────┐        ┌──────────────────┐
│  Large Interface │        │ Small Interface   │
│  many params     │        │ few params        │
│  many methods    │        │ few methods       │
├──────────────────┤        ├──────────────────┤
│ Thin             │        │                  │
│ Implementation   │        │  Deep            │
│                  │        │  Implementation  │
└──────────────────┘        │  (complex logic  │
                            │   hidden inside) │
                            │                  │
                            └──────────────────┘
```

## Why This Matters for TDD

- **Small interface** = fewer tests needed to cover the contract
- **Deep implementation** = complex logic is encapsulated and testable through the interface
- Tests stay stable when implementation changes (because the interface doesn't change)

## Example: Todo API

### Shallow (hard to test, brittle)
```typescript
// Too many methods, too much surface area
class TodoService {
  validateTitle(title: string): boolean
  sanitizeInput(input: object): object
  checkDuplicates(title: string): Promise<boolean>
  insertIntoDb(todo: object): Promise<number>
  formatResponse(todo: object): object
  notifyWebhook(event: string, data: object): void
  createTodo(title: string): Promise<Todo>
}
```

### Deep (easy to test, stable)
```typescript
// Small interface, deep implementation
class TodoService {
  create(title: string): Promise<Todo>
  list(filters?: TodoFilters): Promise<Todo[]>
  complete(id: number): Promise<Todo>
  delete(id: number): Promise<void>
}
```

The deep module hides validation, sanitization, deduplication, persistence, and notifications behind four simple methods. Tests only need to verify behaviour through these four methods.

## Design Guideline

When planning your interface before TDD:
1. What does the **consumer** need? (Not what the implementation needs)
2. Can you reduce the number of methods/params?
3. Would a consumer understand this interface WITHOUT reading the implementation?
4. Does changing the implementation require changing the interface? (It shouldn't)
