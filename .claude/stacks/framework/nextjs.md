---
assumes: []
packages:
  runtime: [next, react, react-dom]
  dev: [typescript, "@types/react", "@types/node", eslint, eslint-config-next]
files:
  - .nvmrc
  - src/app/layout.tsx
  - src/app/page.tsx
  - src/app/not-found.tsx
  - src/app/error.tsx
  - src/components/RetainTracker.tsx
env:
  server: []
  client: []
ci_placeholders: {}
clean:
  files: [.nvmrc, package.json, package-lock.json, tsconfig.json, next.config.ts, next-env.d.ts]
  dirs: [node_modules, .next, out]
gitignore: [.next/, out/]
---
# Framework: Next.js (App Router)
> Used when idea.yaml has `stack.framework: nextjs`

## Packages
```bash
npm install next react react-dom
npm install -D typescript @types/react @types/node eslint eslint-config-next
```

## Project Setup
- `.nvmrc`: containing `20` (used by CI and local version managers)
- `package.json`: `scripts` with `dev`, `build`, `start`, `lint` and `engines: { "node": ">=20" }`
- `tsconfig.json`: enable `strict: true` and `@/` path alias mapping to `src/`
- `next.config.ts`: minimal, no custom config

## File Structure
```
src/
  app/              # App Router pages and API routes
    layout.tsx      # Root layout — <html>, <body>, metadata, globals.css import
    page.tsx        # Landing page (/)
    not-found.tsx   # 404 page with link back to /
    error.tsx       # Error boundary with "use client", user-friendly message, retry button
    api/            # API route handlers (all mutations go here)
      <resource>/
        route.ts    # Route handler
    <page-name>/    # One folder per idea.yaml page
      page.tsx      # Page component
  components/       # Reusable UI components
    ui/             # UI library components (auto-generated)
  lib/              # Utilities (analytics, database clients, types, etc.)
```

## Page Conventions
- Default to `"use client"` for all page and component files
- One `page.tsx` per route folder
- `layout.tsx` for root layout only
- Import analytics tracking functions in every page that fires events (see analytics stack file for exports)

## API Route Conventions
- Route handlers in `src/app/api/<resource>/route.ts`
- Validate all input with zod
- Return `{ error: string }` with appropriate HTTP status codes on failure
- Use try/catch, return user-friendly error messages

## Data Fetching
- Client-side: `fetch` in useEffect or SWR
- Server-side (API routes): direct database calls via server client

## Restrictions
- No Server Actions — use API routes for all mutations
- No caching configuration (`revalidate`, `cache`, etc.)
- No parallel routes or intercepting routes

## retain_return Tracking
Create a client component for retain_return tracking and render it in the root layout. This keeps the root layout as a server component (required for `metadata` export) while running client-side localStorage logic in a separate component.

### `src/components/RetainTracker.tsx` — Client component
```tsx
"use client";

import { useEffect } from "react";
import { trackRetainReturn } from "@/lib/events";

export function RetainTracker() {
  useEffect(() => {
    try {
      const lastVisit = localStorage.getItem("last_visit_ts");
      if (lastVisit) {
        const days = Math.floor((Date.now() - Number(lastVisit)) / 86_400_000);
        if (days >= 1) {
          trackRetainReturn({ days_since_last: days });
        }
      }
      localStorage.setItem("last_visit_ts", String(Date.now()));
    } catch {
      // localStorage unavailable — skip silently
    }
  }, []);

  return null;
}
```

In the root layout (a server component — do NOT add "use client" to layout.tsx):
```tsx
import { RetainTracker } from "@/components/RetainTracker";

// Inside the <body> tag:
<RetainTracker />
```

## Security
- All `"use client"` components run in the browser — never import server-only secrets or database admin clients in client components
- API route handlers (`src/app/api/`) run server-side — use them for all mutations and sensitive operations
- Validate all API route inputs with zod before processing
- Return generic error messages to the client — do not leak stack traces or internal details

## PR Instructions
- No additional framework setup needed after merging — `npm install && npm run dev` is sufficient
