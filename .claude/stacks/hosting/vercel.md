---
assumes: [framework/nextjs]
packages:
  runtime: []
  dev: []
files:
  - src/app/api/health/route.ts
env:
  server: []
  client: []
ci_placeholders: {}
clean:
  files: []
  dirs: []
gitignore: [.vercel/]
---
# Hosting: Vercel
> Used when idea.yaml has `stack.hosting: vercel`
> Assumes: `framework/nextjs` (references `NEXT_PUBLIC_` env var prefix convention)

## Deployment
```bash
npx vercel deploy --prod
```

## Auto-Deploy on Merge
- Vercel's GitHub integration auto-deploys to production on every push/merge to `main`
- Preview deployments are created automatically on PRs (used by `preview-smoke` CI job)
- `make deploy` remains available for manual CLI deploys and first-time project linking
- Skills should not include `make deploy` as a required iteration step — merging to `main` is sufficient

## Health Check

### `src/app/api/health/route.ts` — Deployment health endpoint

Bootstrap creates this endpoint unconditionally. It always returns basic status; service-specific checks are added based on the active stack.

**Base template (always created):**
```ts
import { NextResponse } from "next/server";

export async function GET() {
  const checks: Record<string, string> = { status: "ok" };
  // Service checks are added by bootstrap based on active stack services.
  // Each returns "ok" or an error message.
  return NextResponse.json(checks);
}
```

**When `stack.database` is present:** bootstrap adds a database connectivity check inside the function body — import the server client, run a lightweight query (e.g., `supabase.from('...').select('id').limit(1)`), and set `checks.database = "ok"` or the error message.

**When `stack.auth` is present:** bootstrap adds an auth service check — call `supabase.auth.getUser()` with no session (expects an auth error, not a network error), and set `checks.auth = "ok"` or the error message.

**Response:** Returns 200 with JSON `{ status: "ok", ... }` if all checks pass. Returns 503 if any check fails, with individual check results so failures are diagnosable.

## Preview Smoke Test

Vercel automatically creates preview deployments on PRs. CI runs page-load smoke tests against the preview URL before merge.

- No auth, no database writes, no Docker required
- Reuses existing `e2e/smoke.spec.ts` via `E2E_BASE_URL` pointed at the preview URL
- PR-only (`github.event_name == 'pull_request'`) — pushes to main don't create preview deployments
- Uses `patrickedqvist/wait-for-vercel-preview` GitHub Action to get the preview URL

See the testing stack file's "Preview Smoke CI Job Template" section for the CI job template.

## Environment Variables
- Set via **Vercel dashboard -> Project -> Settings -> Environment Variables**
- Client-side env vars must use `NEXT_PUBLIC_` prefix
- Never commit secrets to code — always use environment variables

## Rate Limiting Limitation
Simple in-memory counters do not persist across serverless invocations on Vercel, so they are not effective for rate limiting.

For auth and payment API routes:
- Add `// TODO: Add production rate limiting (e.g., Upstash Redis)` comment at the top of the route handler
- If idea.yaml `stack` includes a rate-limiting service (e.g., Upstash), use that instead
- Mention this limitation in the PR body so the user knows to address it before production

## Patterns
- Vercel auto-deploys to production when PRs are merged to `main` (requires GitHub integration)
- Deploy with `npx vercel deploy --prod` for manual production deployments
- After manual `make deploy`, the health endpoint is automatically checked
- Use Vercel's preview deployments (automatic on PRs) for testing before production
- Preview deployments are smoke-tested in CI before merge
- Client-side environment variables must use the `NEXT_PUBLIC_` prefix
- Environment variables are configured per-environment (Production, Preview, Development) in the Vercel dashboard

## PR Instructions
- After merging, ensure all environment variables from `.env.example` are set in Vercel: Project → Settings → Environment Variables
- First deploy will prompt to link the repository to a Vercel project — follow the CLI prompts
