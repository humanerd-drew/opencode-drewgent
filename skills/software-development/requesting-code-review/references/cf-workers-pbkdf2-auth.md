# Email/Password Auth on Cloudflare Workers (Web Crypto PBKDF2)

Password authentication on Cloudflare Workers without npm dependencies,
using the Web Crypto API (SubtleCrypto) which Workers supports natively.

## Design

```
POST /api/auth/register  { email, password, name? }  → 201 + user
POST /api/auth/login     { email, password }          → 200 + session cookie
```

## Implementation

### Password Hashing (PBKDF2 + SHA-256, 100k iterations)

```typescript
async function hashPassword(password: string): Promise<string> {
    const encoder = new TextEncoder();
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const key = await crypto.subtle.importKey(
        'raw', encoder.encode(password),
        'PBKDF2', false, ['deriveBits']
    );
    const hash = await crypto.subtle.deriveBits(
        { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
        key, 256
    );
    const combined = new Uint8Array(salt.length + hash.byteLength);
    combined.set(salt);
    combined.set(new Uint8Array(hash), salt.length);
    return btoa(String.fromCharCode(...combined));
}
```

### Password Verification (Timing-Safe-ish)

```typescript
async function verifyPassword(password: string, stored: string): Promise<boolean> {
    try {
        const encoder = new TextEncoder();
        const raw = Uint8Array.from(atob(stored), c => c.charCodeAt(0));
        const salt = raw.slice(0, 16);
        const oldHash = raw.slice(16);
        const key = await crypto.subtle.importKey(
            'raw', encoder.encode(password),
            'PBKDF2', false, ['deriveBits']
        );
        const newHash = await crypto.subtle.deriveBits(
            { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
            key, 256
        );
        const newArr = new Uint8Array(newHash);
        return newArr.length === oldHash.length
            && newArr.every((v, i) => v === oldHash[i]);
    } catch { return false; }
}
```

### Stored Format

Base64 of: `[16-byte salt][32-byte hash]` = 48 bytes → 64 base64 chars.

Stored in D1 `users` table:
```sql
ALTER TABLE users ADD COLUMN password_hash TEXT;
CREATE INDEX idx_users_email ON users(email);
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| PBKDF2 (not bcrypt/scrypt) | Web Crypto API native; no npm deps needed on CF Workers |
| 100,000 iterations | Good balance of security and Worker CPU time (≤200ms) |
| Salt + hash in single base64 field | No separate salt column needed |
| `catch { return false }` on verify | Timing-safe: same path for wrong-password and malformed-hash |
| Email uniqueness via D1 UNIQUE constraint | Catches duplicate registration server-side |

## Route Registration

```typescript
import { handleRegister, handleLogin } from './src/controllers/auth';

// worker.ts:
if (url.pathname === '/api/auth/register' && request.method === 'POST')
    return handleRegister(request, env, url);
if (url.pathname === '/api/auth/login' && request.method === 'POST')
    return handleLogin(request, env, url);
```

## Dev-Only Login Bypass (No DB Needed)

For local development when D1 tables don't exist:

```typescript
// Only works when env.IS_LOCAL_DEV === 'true'
// Creates a session and redirects to /app/ (no DB write)
export async function handleDevLogin(request, env, url): Promise<Response> {
    // check IS_LOCAL_DEV
    // create session for dev_* user id
    // 302 redirect to /app/ with Set-Cookie
}
```

Route: `GET /api/auth/dev-login` → 302 to `/app/` with session cookie.
