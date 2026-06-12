# QA — command commands

Deterministic QA for command routers and route playbooks in `~/.cursor/commands/**/*.md`.

## Procedure

1. Load every `*.md` under `~/.cursor/commands/`.
2. Validate each file has exactly one `#` title, and exactly one `## Trigger`, `## Steps`, and `## Notes` in that order.
3. Validate P9: every public command and private function file except `commands.md` declares exactly one `**Dispatch:**` and `**Search phrases:**` line in that order, declares no legacy `**Slash:**`, `**Signature:**`, or `**Prose dispatch:**` lines, and contains no user-facing slash command invocation prose.
4. Validate trigger boundaries: invocable dispatch forms do not appear under `Search phrases`, search phrases do not replace dispatch entries, and legacy `**Phrases:**` blocks fail.
5. Validate phrase-to-route exactness for invocable entries only: no dispatch value appears in more than one command/function route file, except the documented `(test)` router and `commands/test/index.md` implementation mirror. `Search phrases` may repeat because they are non-invocable discovery aids.
6. Validate quote shape for declared invocation forms: single-quoted wrappers fail with `invalid quote: single quotes are not a valid wrapper; use double quotes`.
7. Validate each file is <= 250 lines.
8. Validate namespace routers resolve routes to grouped route playbook paths.
9. Validate catalog integrity: `commands.md` links every public command file.
10. Validate catalog integrity: the generated roster block in `commands.md` matches filesystem state (`platform/tooling/sync-commands-catalog.sh --check`).
11. Validate command advisory coverage and rendering: v0 advisory namespaces have exactly one effective default or explicit not-applicable marker per invocable route, role overrides are non-orphan and differentiated, aliases resolve through `platform/data/capability-aliases.json` and `platform/data/effort-tiers.json`, and caller-facing generated output does not leak runtime policy fields or concrete model identities.
12. Validate command links stay inside `commands/`, core policy, core policy, and `tests/specs/`.
13. Validate dependencies align with rule routers (core policy, core policy).

## Required roster

Public command files under `~/.cursor/commands/`:

- `agent/index.md`
- `commands.md`
- `collab/index.md`
- `collab/speak/index.md`
- `doc/index.md`
- `quality/index.md`
- `git/index.md`
- `test/index.md`

## Output

Return a pass/fail report by check (`P1..Pn`) and list exact file paths for failures.

## Secondary validation

When environment allows, run:

- `./tests/run.sh`
- `./platform/tooling/audit.sh`
