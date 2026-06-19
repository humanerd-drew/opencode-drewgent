# Hono Migration: Concrete Pattern from m-log-v2

## wrapHandler Bridge (CF Workers → Hono)

CF Workers handlers have `(request, env, url, ctx?)` signature. Hono handlers take `Context`. Bridge pattern:

```typescript
import { Hono } from 'hono'
import type { Context } from 'hono'

function wrapHandler(fn: (req: Request, env: any, url: URL, ctx?: any) => Promise<Response>) {
  return async (c: Context) => {
    const request = c.req.raw
    const url = new URL(request.url)
    if (fn.length >= 4) {
      return fn(request, c.env, url, c.executionCtx)
    }
    return fn(request, c.env, url)
  }
}

export const routes = new Hono()
routes.post('/analyze', wrapHandler(handleAnalyze))
```

## zValidator + request.json() Conflict

`zValidator('json', schema)` consumes the request body stream. If the downstream handler called via `wrapHandler` then calls `request.json()`, it gets `TypeError: Body has already been consumed`.

**Fix options** (in order of preference):

1. **Skip zValidator on unrefactored routes**: If handlers still call `request.json()`, don't use zValidator on that route yet.
2. **Pass validated data**: Refactor handler to accept `c.req.valid('json')` directly:
   ```typescript
   routes.post('/analyze', zValidator('json', schema), async (c) => {
     const data = c.req.valid('json')
     return handleAnalyzeWithData(data, c.env)
   })
   ```
3. **Clone request**: Read body before zValidator (not recommended — defeats purpose).

## Middleware that Was Inside if/else (injectAnalysisReport)

Original worker.ts had inline processing after handler calls:
```typescript
const response = await handleAnalyze(request, env, url, ctx)
return await injectAnalysisReport(response, env)  // ← NOT app.use()
```

When migrated to Hono, this disappeared because it was code inside an if block, not a registered middleware.

**Correct migration**:
```typescript
// Option A: Wrap into route handler
routes.post('/analyze', async (c) => {
  const resp = await handleAnalyze(c.req.raw, c.env, new URL(c.req.url), c.executionCtx)
  return await injectAnalysisReport(resp, c.env)
})

// Option B: As Hono middleware
app.use('/api/analyze', async (c, next) => {
  await next()
  if (c.res.status === 200) {
    c.res = await injectAnalysisReport(c.res, c.env)
  }
})
```

## Route File Template (route-xxx.ts)

```typescript
import { Hono } from 'hono'
import type { Context } from 'hono'
import { z } from 'zod'
import { zValidator } from '@hono/zod-validator'
import { handlerFn } from '../domain/some-file'

export const routes = new Hono()

// ── Schemas ──
const schema = z.object({
  field: z.string(),
})

// ── Routes ──
routes.post('/endpoint', zValidator('json', schema), wrapHandler(handlerFn))
routes.get('/other', wrapHandler(otherFn))

function wrapHandler(fn: (req: Request, env: any, url: URL, ctx?: any) => Promise<Response>) {
  return async (c: Context) => {
    const request = c.req.raw
    const url = new URL(request.url)
    if (fn.length >= 4) return fn(request, c.env, url, c.executionCtx)
    return fn(request, c.env, url)
  }
}
```
