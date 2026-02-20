---
assumes: [framework/nextjs]
packages:
  runtime: ["@supabase/supabase-js", "@supabase/ssr"]
  dev: []
files:
  - src/lib/supabase.ts
  - src/lib/supabase-server.ts
  - src/lib/types.ts
env:
  server: []
  client: [NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY]
ci_placeholders:
  NEXT_PUBLIC_SUPABASE_URL: "https://placeholder.supabase.co"
  NEXT_PUBLIC_SUPABASE_ANON_KEY: placeholder-anon-key
clean:
  files: []
  dirs: []
gitignore: []
---
# Database: Supabase (Postgres)
> Used when idea.yaml has `stack.database: supabase`
> Assumes: `framework/nextjs` (server client uses `next/headers` for cookies)

## Packages
```bash
npm install @supabase/supabase-js @supabase/ssr
```

## Files to Create

### `src/lib/supabase.ts` — Browser client
```ts
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

### `src/lib/supabase-server.ts` — Server client for API routes
```ts
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createServerSupabaseClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
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
- Use this in all API route handlers (`src/app/api/`) and Server Components
- Import `cookies` from `next/headers` (server-only)
- The cookie-based approach preserves the user's auth session server-side

## Environment Variables
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## Schema Management
- SQL migrations go in `supabase/migrations/` as numbered files (`001_initial.sql`, `002_feature.sql`, etc.)
- Use `CREATE TABLE IF NOT EXISTS` for tables and `DROP POLICY IF EXISTS ... ; CREATE POLICY ...` for RLS policies (safe to re-run — `CREATE POLICY IF NOT EXISTS` is not valid PostgreSQL)
- Every table must have:
  - `id uuid DEFAULT gen_random_uuid() PRIMARY KEY`
  - `created_at timestamptz DEFAULT now()`
- User-owned tables must have:
  - `user_id uuid REFERENCES auth.users(id) NOT NULL`
- `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` on every table
- RLS policies: `auth.uid() = user_id`
- Add SQL comments explaining each table's purpose
- The user runs each migration manually in **Supabase Dashboard -> SQL Editor**

## Types
- Create TypeScript types matching table schemas in `src/lib/types.ts`

## Security
- Never expose `service_role` key to the client
- Always use RLS — never trust the client
- Use the server client (`supabase-server.ts`) in all API route handlers

## Patterns
- Browser client (`supabase.ts`) for client-side components
- Server client (`supabase-server.ts`) for API routes — always verify session server-side
- When creating a new migration, use the next sequential number after existing migrations. Note: concurrent branches may create conflicting numbers (e.g., two branches both create `002_*.sql`) — resolve by renumbering the later-merged migration at merge time. This is acceptable for MVP workflows.

## PR Instructions
- When creating migrations, add to the PR body: "After merging, run `supabase/migrations/<filename>.sql` in your Supabase Dashboard -> SQL Editor"
