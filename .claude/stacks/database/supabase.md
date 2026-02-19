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
- Use `CREATE TABLE IF NOT EXISTS` and `CREATE POLICY IF NOT EXISTS` (safe to re-run)
- Every table must have:
  - `id uuid DEFAULT gen_random_uuid() PRIMARY KEY`
  - `created_at timestamptz DEFAULT now()`
- User-owned tables must have:
  - `user_id uuid REFERENCES auth.users(id) NOT NULL`
- `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` on every table
- RLS policies: `auth.uid() = user_id`
- Add SQL comments explaining each table's purpose
- Migrations are applied automatically by CI on merge to `main` (via `supabase db push`). For manual use: `make migrate`. Fallback: copy SQL into Supabase Dashboard -> SQL Editor.

## Local Development (when `stack.testing` is present)

When the project has `stack.testing` configured, E2E tests run against a **local** Supabase instance instead of the remote project. This keeps tests isolated, fast, and secret-free.

- `supabase init` creates `supabase/config.toml` (commit this file — it configures the local instance)
- `supabase start` starts local Postgres + Auth + API (requires Docker Desktop)
- `supabase db reset` applies all migrations from `supabase/migrations/`
- `supabase stop` shuts down the local instance

## Remote Migration (Production)

Migrations are pushed to the remote Supabase database using `supabase db push`. This happens automatically in CI on merge to `main`, or manually via `make migrate`.

### One-time setup (local `make migrate`)
1. Run `npx supabase login` to authenticate the CLI
2. Run `npx supabase link --project-ref <ref>` to link to your remote project
   - Find your project ref: Supabase Dashboard → Settings → General → Reference ID
3. Set `SUPABASE_DB_PASSWORD` in your shell: `export SUPABASE_DB_PASSWORD=your-password`
   - Find it: Supabase Dashboard → Settings → Database → Database password
4. Run `make migrate`

### One-time setup (CI auto-migration)
Add three GitHub repository secrets (repo → Settings → Secrets and variables → Actions):
| Secret | Where to find it |
|--------|-----------------|
| `SUPABASE_PROJECT_REF` | Supabase Dashboard → Settings → General → Reference ID |
| `SUPABASE_DB_PASSWORD` | Supabase Dashboard → Settings → Database → Database password |
| `SUPABASE_ACCESS_TOKEN` | [supabase.com/dashboard/account/tokens](https://supabase.com/dashboard/account/tokens) → Generate new token |

### Deterministic local keys

These keys are hardcoded in the local Supabase instance and are safe to commit in test configuration. They only work against the local instance — never against a remote project.

- **URL:** `http://127.0.0.1:54321`
- **Anon key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0`
- **Service role key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU`

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
- When creating migrations, add to the PR body: "After merging, CI will automatically apply `supabase/migrations/<filename>.sql` to the remote database. If CI migration secrets are not configured, run `make migrate` or apply the SQL manually in Supabase Dashboard -> SQL Editor."
