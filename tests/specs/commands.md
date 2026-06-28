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
12. Validate command links stay inside `commands/`, platform standards, and `tests/specs/`.
13. Validate dependencies align with platform standards.

## Required roster

Public command routers under `~/.cursor/commands/`:

- `agent/index.md`
- `commands.md`
- `collab/index.md`
- `doc/index.md`
- `git/index.md`
- `help/index.md`
- `quality/index.md`
- `test/index.md`

Route playbooks under `~/.cursor/commands/`:

- `agent/install/index.md`
- `agent/patch/index.md`
- `agent/upgrade/index.md`
- `collab/activate/index.md`
- `collab/advance/index.md`
- `collab/archive/index.md`
- `collab/close/index.md`
- `collab/delete/index.md`
- `collab/diff/index.md`
- `collab/export-issues/index.md`
- `collab/init/index.md`
- `collab/join/index.md`
- `collab/list/index.md`
- `collab/log/index.md`
- `collab/open/index.md`
- `collab/participant-verify/index.md`
- `collab/remove-participant/index.md`
- `collab/reopen/index.md`
- `collab/restore/index.md`
- `collab/retract-speak/index.md`
- `collab/rewrite-execution/index.md`
- `collab/rewrite-speak/index.md`
- `collab/rewrite-summary/index.md`
- `collab/run-plan/index.md`
- `collab/seal-verification/index.md`
- `collab/set/index.md`
- `collab/show-flags/index.md`
- `collab/show-policy/index.md`
- `collab/show-verdict/index.md`
- `collab/speak/index.md`
- `collab/status/index.md`
- `collab/summarize/index.md`
- `collab/unset/index.md`
- `collab/write-summary/index.md`
- `doc/write-changelog/index.md`
- `doc/write-manual/index.md`
- `doc/write-readme/index.md`
- `git/commit/index.md`
- `git/issue/index.md`
- `quality/assess-game/index.md`
- `quality/assess-interface/index.md`
- `quality/assess-operations/index.md`
- `quality/assess-web/index.md`
- `quality/show-notes/index.md`
- `quality/tune/index.md`

## Output

Return a pass/fail report by check (`P1..Pn`) and list exact file paths for failures.

## Secondary validation

When environment allows, run:

- `./tests/run.sh`
- `./platform/tooling/audit.sh`
