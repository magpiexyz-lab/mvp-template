---
assumes: [framework/nextjs]
packages:
  runtime: []
  dev: []
files: []
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
- Deploy with `npx vercel deploy --prod` for production deployments
- Use Vercel's preview deployments (automatic on PRs) for testing before production
- Client-side environment variables must use the `NEXT_PUBLIC_` prefix
- Environment variables are configured per-environment (Production, Preview, Development) in the Vercel dashboard

## PR Instructions
- After merging, ensure all environment variables from `.env.example` are set in Vercel: Project → Settings → Environment Variables
- First deploy will prompt to link the repository to a Vercel project — follow the CLI prompts
