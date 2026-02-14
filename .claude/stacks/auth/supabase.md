---
assumes: [framework/nextjs]
packages:
  runtime: []
  dev: []
files:
  - src/app/signup/page.tsx
  - src/app/login/page.tsx
  - src/lib/supabase-auth.ts
  - src/lib/supabase-auth-server.ts
env:
  server: []
  client: []
ci_placeholders: {}
clean:
  files: []
  dirs: []
gitignore: []
---
# Auth: Supabase Auth
> Used when idea.yaml has `stack.auth: supabase`
> Assumes: `framework/nextjs` (server-side auth check uses `NextResponse`)

## Packages
Shares the same packages as `database/supabase` — no additional installs needed when `stack.database` is also `supabase`.

If `stack.database` is NOT supabase, install:
```bash
npm install @supabase/supabase-js @supabase/ssr
```

## Signup/Login UI
- Use Supabase Auth UI or simple email/password forms
- Signup page: email + password fields, submit button
- Login page: email + password fields, submit button, link to signup
- Enforce a minimum password length of 8 characters on the signup form
- Recommend enabling email verification in Supabase Dashboard (Authentication → Settings → Email Auth → "Confirm email")

## Files to Create

### `src/app/signup/page.tsx` — Signup page (if `signup` is in idea.yaml pages)

#### When `stack.database` is also `supabase` (shared client):
```tsx
"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase";
import { trackSignupStart, trackSignupComplete } from "@/lib/events";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const supabase = createClient();

  useEffect(() => { trackSignupStart({ method: "email" }); }, []);

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    setError("");
    const { error: authError } = await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (authError) { setError(authError.message); return; }
    trackSignupComplete({ method: "email" });
    // TODO: Redirect to post-signup page (e.g., dashboard)
  }

  return (
    <form onSubmit={handleSignup} className="space-y-4">
      <div>
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" placeholder="you@example.com" value={email}
          onChange={e => setEmail(e.target.value)} required />
      </div>
      <div>
        <Label htmlFor="password">Password</Label>
        <Input id="password" type="password" placeholder="Min 8 characters" value={password}
          onChange={e => setPassword(e.target.value)} required minLength={8} />
      </div>
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <Button type="submit" disabled={loading}>
        {loading ? "Creating account..." : "Sign up"}
      </Button>
    </form>
  );
}
```

#### When `stack.database` is NOT supabase (standalone client):
Replace the import on line 3 of the signup page:
```tsx
// Instead of: import { createClient } from "@/lib/supabase";
import { createAuthClient as createClient } from "@/lib/supabase-auth";
```
This aliasing keeps the rest of the component code identical — only the import changes.

- Adapt this pattern for your app — update imports, add fields, and adjust redirects
### `src/app/login/page.tsx` — Login page (if `login` is in idea.yaml pages)

Follows the same structure as the signup page above, with these differences:
- Calls `supabase.auth.signInWithPassword()` instead of `signUp()`
- No password minimum-length validation (existing accounts may have any length)
- No analytics events (EVENTS.yaml defines no login event)

#### When `stack.database` is also `supabase` (shared client):
```tsx
"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const supabase = createClient();

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (authError) { setError(authError.message); return; }
    // TODO: Redirect to post-login page (e.g., dashboard)
  }

  return (
    <form onSubmit={handleLogin} className="space-y-4">
      <div>
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" placeholder="you@example.com" value={email}
          onChange={e => setEmail(e.target.value)} required />
      </div>
      <div>
        <Label htmlFor="password">Password</Label>
        <Input id="password" type="password" placeholder="Password" value={password}
          onChange={e => setPassword(e.target.value)} required />
      </div>
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <Button type="submit" disabled={loading}>
        {loading ? "Logging in..." : "Log in"}
      </Button>
      <p className="text-sm text-muted-foreground">
        Don't have an account? <a href="/signup" className="underline">Sign up</a>
      </p>
    </form>
  );
}
```

#### When `stack.database` is NOT supabase (standalone client):
Replace the import on line 3 of the login page:
```tsx
// Instead of: import { createClient } from "@/lib/supabase";
import { createAuthClient as createClient } from "@/lib/supabase-auth";
```

## Client-Side Auth State
- Use `supabase.auth.onAuthStateChange()` in components to react to auth changes
- On login/signup success, redirect to the appropriate page

## Server-Side Auth Check
In API route handlers, verify the user session before processing the request. The import depends on whether `stack.database` is also `supabase`.

#### When `stack.database` is also `supabase` (shared client):
```ts
import { NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase-server";

// At the start of your route handler:
const supabase = await createServerSupabaseClient();
const { data: { user } } = await supabase.auth.getUser();
if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
// Use user.id for database queries and metadata
```

#### When `stack.database` is NOT supabase (standalone client):
```ts
import { NextResponse } from "next/server";
import { createServerAuthClient } from "@/lib/supabase-auth-server";

// At the start of your route handler:
const supabase = await createServerAuthClient();
const { data: { user } } = await supabase.auth.getUser();
if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
// Use user.id for database queries and metadata
```

## Analytics Integration
- Fire `signup_start` on form render (include `method` property: `"email"`, `"google"`, `"github"`)
- Fire `signup_complete` on successful account creation (include `method` property)

## Shared Client Note
When `stack.auth` matches `stack.database` (both `supabase`), they share the same client files (`supabase.ts` and `supabase-server.ts`). When different, auth needs its own library file — see "Standalone Client" below.

### Standalone Client (when `stack.database` is not supabase)

If `stack.database` is NOT supabase, the shared client files don't exist. Create auth-specific clients:

#### `src/lib/supabase-auth.ts` — Browser client for auth
```ts
import { createBrowserClient } from "@supabase/ssr";

export function createAuthClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

#### `src/lib/supabase-auth-server.ts` — Server client for auth
```ts
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createServerAuthClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll(); },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        },
      },
    }
  );
}
```

Update signup/login page imports to use `createAuthClient` from `@/lib/supabase-auth` instead of `@/lib/supabase`.

## Environment Variables
When `stack.database` is also `supabase`, auth shares the database environment variables (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`). No additional env vars needed.

When `stack.database` is NOT supabase, add these env vars for auth:
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## PR Instructions
- After merging, enable email verification in Supabase Dashboard: Authentication → Settings → Email Auth → "Confirm email"
- Test the signup flow end-to-end: create an account, verify email (if enabled), confirm user appears in Authentication → Users
