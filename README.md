# dotcursor

Configuration framework for `~/.cursor` command routes and agent harnesses.

## Entry points

Each adapter is a thin routing-only file that points to `commands/commands.md` as the shared command catalog.

| Adapter | For | Bootstrap chain |
|---|---|---|
| `CLAUDE.md` | Claude Code CLI | `CLAUDE.md` → `AGENTS.md` → `commands/commands.md` |
| `AGENTS.md` | Codex, GPT, and other agent harnesses | `AGENTS.md` → `commands/commands.md` |

## Directory layout

```
~/.cursor/
├── CLAUDE.md          — Claude Code adapter (routing only)
├── AGENTS.md          — other-harness adapter (routing only)
├── README.md          — this file
├── .collab.json       — checked-in collab repo marker
├── commands/          — command catalog, routers, route playbooks, and slices
│   └── collab/        — collab routes plus engine/, reference/, and data/
├── platform/          — shared cross-namespace infrastructure
│   ├── standards/     — cross-cutting invariants and contracts
│   ├── tooling/       — framework tooling and validators
│   ├── templates/     — scaffolding templates
│   └── data/          — shared advisory vocabulary and platform data
├── generated/         — framework-generated catalogs (do not edit by hand)
└── tests/             — agent-facing and shell QA harnesses
```

### `generated/` discovery

Files under `generated/` are produced by scripts in `platform/tooling/`. Edit the source files or templates, then re-run the relevant sync script — do not edit `generated/` directly.

## User-scope collab state root

`$HOME/.collabs/<projectId>/` is a fourth operating plane that holds live collab records and transcripts for this repository. The directory lives outside the repository tree and survives `git clean`, `/compact`, and agent swaps. `.collab.json` at the repo root is the tracked marker that binds this directory to the repo; agents resolve the state root by reading `.collab.json` and reading the `projectId` from it.

The state root is excluded from git — it is never source, never deployed, and never committed. The state root is the durable runtime side of the collab system: what the registry writes, agents read, and seals are computed against.

## Prerequisites

Before running the tooling, ensure the host satisfies [`platform/standards/runtime-contract.md`](platform/standards/runtime-contract.md): Python ≥ 3.9, bash ≥ 3.2, `git` and `python3` on `$PATH`, and stdlib-only Python tooling (no third-party packages).

## Setup

Run `platform/tooling/install-git-hooks.sh` to install pre-commit and pre-push hooks that run the full test suite before history moves. Pass `--no-verify` to `git commit` or `git push` to skip the hooks. Force-push blocking and deletion blocking on `main` are manual GitHub repository settings, not a source patch.

## Done signal

Run `platform/tooling/audit.sh` to verify the framework surface. The audit exits 0 when:

- Runtime paths (`$HOME/.collabs/<projectId>/` (a readable slug), `.claude/`, `projects/`) are excluded from git
- No accidental untracked payload
- Every tracked file is reachable from an adapter, platform document, or catalog entry
- Framework-generated output is distinguishable from generated output
- Reference graph has no broken links
