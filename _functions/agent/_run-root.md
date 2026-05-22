# /agent Run-Root Boundary

Shared run-root vocabulary for scaffold-mutating `/agent` routes.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** agent run root, global runtime root, target repository root

## Steps

1. Read this document before changing `/agent install`, `/agent patch`, or `/agent upgrade` run-root checks.
2. Cite this document from any `/agent` route that distinguishes the installed dotcommand tree from a repository being scaffolded.
3. Do not mutate repository state from this documentation-only reference.

## Notes

- **Global runtime root:** The installed dotcommand tree at `~/.cursor`, containing runtime command, rule, template, role, and helper sources.
- **Target repository root:** The git repository root for the project receiving or maintaining scaffold files such as `CLAUDE.md`, `AGENTS.md`, and `REPOSITORY.md`. This repository may also be developed in place at `~/.cursor`; in that case the same path is both the global runtime root and the target repository root.
- **Boundary:** `/agent install` and `/agent upgrade` must run from a git repository root. They read template source from `~/.cursor/_templates/` and write only the scaffold files in the current target repository root; a target path of `~/.cursor` is permitted.
- **Placement rationale:** This reference lives under `_functions/agent/` because the boundary is currently scoped to `/agent` scaffold-mutating routes. Move it to `_core/` only if a non-`/agent` route needs the same vocabulary.
