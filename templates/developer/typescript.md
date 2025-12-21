{% extends "_base.md" %}

# TypeScript Developer

## Additional TypeScript Rules

- Strict mode enabled
- Use interfaces for data structures
- Prefer `const` over `let`
- Use async/await, no callbacks
- ESLint + Prettier for formatting

## Import Structure

```typescript
// External
import { z } from 'zod';

// Internal
import { Logger } from '@helix/observability';
```
