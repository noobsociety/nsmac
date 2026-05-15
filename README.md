# dotcursor

Configuration framework for `~/.cursor` — Cursor IDE, Claude Code, and agent harnesses.

## Entry points

Each adapter is a thin routing-only file that points to `_CURSOR.md` as the shared core.

| Adapter | For | Bootstrap chain |
|---|---|---|
| `CLAUDE.md` | Claude Code CLI | `CLAUDE.md` → `_CURSOR.md` → `commands/commands.md` |
| `AGENTS.md` | Codex, GPT, and other agent harnesses | `AGENTS.md` → `_CURSOR.md` → `commands/commands.md` |
| `rules/auto.mdc` | Cursor IDE (auto-applied at startup) | `rules/auto.mdc` → `_mdc/auto/*` |
| `rules/shared.mdc` | Cursor IDE (applied on request) | `rules/shared.mdc` → `_mdc/shared/*` |

Cursor reads `~/.cursor/rules/*.mdc` at startup. `auto.mdc` is `alwaysApply: true`; `shared.mdc` is `alwaysApply: false`. No separate adapter file is needed — the rules directory is the native Cursor entry surface.

## Directory layout

```
~/.cursor/
├── CLAUDE.md          — Claude Code adapter (routing only)
├── AGENTS.md          — other-harness adapter (routing only)
├── _CURSOR.md         — shared routing core; owns read order, ownership boundaries
├── README.md          — this file
├── _core/             — cross-cutting invariants and contracts
├── _functions/        — slash command implementations
├── _generated/        — framework-generated catalogs (do not edit by hand)
├── _mdc/              — Cursor rule implementations (auto/ and shared/ sub-trees)
├── _roles/            — role definitions for the collab framework
├── _templates/        — scaffolding templates
├── _tests/            — agent-facing QA harnesses for `/test`
├── commands/          — command catalog and routing table
├── rules/             — Cursor startup surfaces (auto.mdc, shared.mdc)
└── tools/             — framework tooling (collab engine, cursor utilities)
```

### `_generated/` discovery

Files under `_generated/` are produced by scripts in `tools/cursor/`. Edit the source files or templates, then re-run the relevant sync script — do not edit `_generated/` directly.

## Setup

Run `tools/cursor/install-git-hooks.sh` to install pre-commit and pre-push hooks that run the full test suite before history moves. Pass `--no-verify` to `git commit` or `git push` to skip the hooks. Force-push blocking and deletion blocking on `main` are manual GitHub repository settings, not a source patch.

## Done signal

Run `tools/cursor/audit.sh` to verify the framework surface. The audit exits 0 when:

- Runtime paths (`.collabs/`, `.claude/`, `projects/`) are excluded from git
- No accidental untracked payload
- Every tracked file is reachable from an adapter, core, or catalog
- Framework-generated output is distinguishable from IDE-produced output
- Reference graph has no broken links
