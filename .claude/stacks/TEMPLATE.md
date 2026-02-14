---
# YAML Frontmatter Schema — every stack file must include this block.
# The validate-frontmatter.py script checks these keys on every PR.
#
# assumes:          list[str]  — other stack files this depends on (e.g., [framework/nextjs])
# packages:
#   runtime:        list[str]  — npm packages installed with `npm install`
#   dev:            list[str]  — npm packages installed with `npm install -D`
# files:            list[str]  — source files this stack creates (relative to repo root)
# env:
#   server:         list[str]  — server-only environment variable names
#   client:         list[str]  — client-side environment variable names (e.g., NEXT_PUBLIC_*)
# ci_placeholders:  dict       — env var name → placeholder value for CI builds
# clean:
#   files:          list[str]  — files to delete on `make clean`
#   dirs:           list[str]  — directories to delete on `make clean`
# gitignore:        list[str]  — entries to add to .gitignore

assumes: []
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
gitignore: []
---
# [Category]: [Technology Name]
> Used when idea.yaml has `stack.[category]: [value]`
> Assumes: [other stack files this depends on, e.g., `framework/nextjs` — or "None"]

## Packages
```bash
npm install [runtime-packages]
npm install -D [dev-packages]
```

## Files to Create
<!-- If this stack creates no files (e.g., hosting/vercel), write "None — this stack provides deployment patterns only." so future authors know the omission is intentional. -->

### `src/lib/[filename].ts` — [Description]
```ts
// Starter code or key exports
```
- [Usage notes]

## Environment Variables
```
VARIABLE_NAME=description-or-example
```

## Patterns
- [How skills should use this technology]
- [Key conventions to follow]
- [What to import and where]

## Assumes
- [List stack files this depends on, e.g., `framework/nextjs` for Next.js-specific imports]
- [If truly generic, write "None"]

<!-- Optional sections — include when relevant: -->

## Security
- [Secrets handling]
- [Access control requirements]
- [Client vs server boundaries]

## Analytics Integration
- [Which EVENTS.yaml events this stack interacts with]
- [Where to fire them]

## PR Instructions
- [Post-merge setup steps for the user]
- [Environment variables to configure]
- [External service configuration]
