# QA — cursor commands

Deterministic QA for public slash routers in `~/.cursor/commands/*.md`.

## Procedure

1. Load every `*.md` under `~/.cursor/commands/`.
2. Validate each file has exactly one `#` title, and exactly one `## Trigger`, `## Steps`, and `## Notes` in that order.
3. Validate P9: every public command and private function file except `commands.md` declares exactly one `**Slash:**`, `**Prose dispatch:**`, and `**Search phrases:**` line in that order.
4. Validate trigger boundaries: invocable slash/prose forms do not appear under `Search phrases`, search phrases do not replace slash/prose entries, and legacy `**Phrases:**` blocks fail.
5. Validate phrase-to-route exactness for invocable entries only: no slash or prose-dispatch value appears in more than one command/function route file, except the documented `/test` router and `_functions/test/run.md` implementation mirror. `Search phrases` may repeat because they are non-invocable discovery aids.
6. Validate quote shape for declared invocation forms: single-quoted wrappers fail with `invalid quote: single quotes are not a valid wrapper; use double quotes`.
7. Validate each file is <= 250 lines.
8. Validate public routers (`narrative.md`, `doc.md`, `git.md`, `quality.md`, `test.md`) resolve routes to grouped function paths.
9. Validate catalog integrity: `commands.md` links every public command file.
10. Validate catalog integrity: the generated roster block in `commands.md` matches filesystem state (`tools/cursor/sync-commands-catalog.sh --check`).
11. Validate command advisory coverage and rendering: v0 advisory namespaces have exactly one effective default or explicit not-applicable marker per invocable route, role overrides are non-orphan and differentiated, aliases resolve through `_data/capability-aliases.json` and `_data/effort-tiers.json`, and caller-facing generated output does not leak runtime policy fields or concrete model identities.
12. Validate command links stay inside `commands/`, `_functions/`, `rules/`, `_mdc/`, and `_tests/`.
13. Validate dependencies align with rule routers (`rules/auto.mdc`, `rules/shared.mdc`) and private rule bodies (`_mdc/auto/*.mdc`, `_mdc/shared/*.mdc`).

## Required roster

Public command files under `~/.cursor/commands/`:

- `agent.md`
- `commands.md`
- `collab.md`
- `doc.md`
- `quality.md`
- `git.md`
- `narrative.md`
- `test.md`

## Output

Return a pass/fail report by check (`P1..Pn`) and list exact file paths for failures.

## Secondary validation

When environment allows, run:

- `./tests/run.sh`
- `./tools/cursor/audit.sh`
