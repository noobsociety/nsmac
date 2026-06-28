# Command grammar

Rules for how `~/.cursor`-routed command notation maps to filesystem and helper names.

## Dispatch surface

Spaced public verbs in dispatch notation — for example `(collab run plan)` and `(collab retract speak)` — are deliberate porcelain over hyphenated filesystem and helper names: the dispatch surface uses word spaces for readability while the backing directories and helper subcommands use the hyphenated form (e.g., `run-plan/index.md`, `retract-speak/index.md`).

## Mapping rule

- A single-word route selector maps unchanged: `(collab init)` → `commands/collab/init/`.
- A multi-word route selector uses the concatenated hyphenated form on disk: `(collab run plan)` → `commands/collab/run-plan/`; `(collab retract speak)` → `commands/collab/retract-speak/`.
- The dispatch surface never uses hyphens as word separators; the filesystem never uses spaces in directory names.

## Stability guarantee

The porcelain/plumbing split is intentional and stable. Adding a new multi-word route must follow the same mapping rule; a route that deviates — using hyphens in its dispatch form or spaces on disk — is a conformance failure detectable by the catalog sync harness.
