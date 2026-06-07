# Repository Contract

Contract between this repository (source plane) and the global agent runtime at `~/.cursor/*`.

## 1) System Model

The contract has three planes:

- **Source plane:** version-controlled files in this repository.
- **Global runtime plane:** `~/.cursor/*`.
- **Project overlay plane:** optional project-local overlay.

Only the source plane is authoritative. Runtime planes are derived execution contexts.

## 2) Authority Chain

Authority is strict and ordered:

1. Repo-owned executable checks and scripts:
   - `./tests/run.sh` (runs `./platform/tooling/audit.sh` then every `tests/**/*.test.sh`)
   - `./platform/tooling/audit.sh` (adapter routing, runtime ignore rules, role-key prose drift guard)
   - `./platform/tooling/check-source-ledger.py --check` (source-ledger schema, retired-trace scan, declared-dependency validation)
   - `./platform/tooling/sync-context-gate.sh --check` (context-gate canonical source/projection parity)
   - `./platform/tooling/audit-role-prose.sh` (role-key prose drift guard for Markdown and MDC surfaces)
   - `./platform/tooling/sync-commands-catalog.sh --check` (commands roster integrity)
   - `./platform/tooling/sync-framework-boundaries.sh` (framework boundary projections)
   - `./platform/tooling/sync-roles-roster.sh` (roles roster projection)
2. Repo-owned source files and policy documents:
   - Root adapters: `CLAUDE.md`, `AGENTS.md`, `REPOSITORY.md`, `README.md`, `.gitignore`, `.collab.json`
   - Public routers and routes: `commands/<namespace>/index.md`, `commands/<namespace>/<route>/index.md`
   - Command advisory source data: shared vocabulary under `platform/data/*.json`, central advisory files under `platform/data/advisories/<ns>.json`, per-slice advisory files under `commands/<ns>/data/<ns>.json` (for example `commands/collab/data/collab.json`), and `platform/data/command-advisory.schema.json`
   - Shared invariants and standards: `platform/standards/*.md`
   - Scaffold templates: `platform/templates/{CLAUDE,AGENTS,REPOSITORY}.md`
   - QA harness: `tests/specs/*.md` (Markdown), `tests/**/*.test.sh` and `tests/run.sh` (shell)
   - Executable tooling: `platform/tooling/*`, `commands/collab/engine/*`
3. Derived runtime or generated outputs:
   - Generated mirrors under `generated/`: `collab-lifecycle.md`, `command-reference.md`, `content-invariants.tsv`, `registry-cli.md` (generator: `commands/collab/engine/registry.py registry-cli-doc`)
   - Generated block `<!-- BEGIN GENERATED:COMMANDS_ROSTER --> ... <!-- END GENERATED:COMMANDS_ROSTER -->` inside `commands/commands.md`
   - Runtime invocation surface at `~/.cursor/*` (this checkout, developed in place)
   - Ignored runtime state (not source): `projects/`, `extensions/`, `ide_state.json`, `plugins/`, `skills/`, `plans/`, `subagents/`

## 3) Output Chain Contract

This repo projects the following root outputs, with deepest dependency chains and validation:

- **Adapter routing surface** — `CLAUDE.md`, `AGENTS.md` route into `commands/commands.md` → `commands/<ns>/index.md` → `commands/<ns>/<route>/index.md`, with cross-references into `platform/standards/*.md`. Validated by `./platform/tooling/audit.sh` and the Markdown harness via `/test commands` and `/test core`.
- **Generated mirrors** — `generated/collab-lifecycle.md`, `generated/command-reference.md`, `generated/content-invariants.tsv`, `generated/registry-cli.md` are derived from `commands/*`, `commands/collab/reference/*`, central advisory files under `platform/data/advisories/*.json`, and per-slice advisory files under `commands/<ns>/data/<ns>.json` such as `commands/collab/data/collab.json`. Regenerated through `commands/collab/engine/lifecycle-doc.py`, `platform/tooling/command-reference.py`, `platform/tooling/sync-framework-boundaries.sh`, and `commands/collab/engine/registry.py registry-cli-doc`.
- **Collab support contracts** — helper output, identity binding, planned-route gates, and registry-state rules live in [`helper-output.md`](commands/collab/reference/helper-output.md), [`identity-contract.md`](commands/collab/reference/identity-contract.md), [`planned-routes.md`](commands/collab/reference/planned-routes.md), and [`registry-state.md`](commands/collab/reference/registry-state.md).
- **Commands roster block** — the `BEGIN GENERATED:COMMANDS_ROSTER` block in `commands/commands.md` is derived from filesystem state under `commands/`. Validated by `./platform/tooling/sync-commands-catalog.sh --check`.
- **Scaffold templates for downstream repos** — `platform/templates/{CLAUDE,AGENTS,REPOSITORY}.md` are copied into target repos by `/agent install` and patched in place by `/agent patch`. Validated by `tests/platform/agent/agent-routes-contract.test.sh`.
- **QA harness surface** — `tests/specs/*.md` and `tests/**/*.test.sh` are the executable proof layer. Validated by `/test all` and `./tests/run.sh`.

## 4) Mutation Protocol and Ownership

- Must edit tracked source only.
- Do not edit by hand:
  - Files under `generated/` — regenerated by `commands/collab/engine/lifecycle-doc.py`, `platform/tooling/command-reference.py`, `platform/tooling/sync-framework-boundaries.sh`, and `commands/collab/engine/registry.py registry-cli-doc` (for `generated/registry-cli.md`).
  - The `BEGIN GENERATED:COMMANDS_ROSTER` ... `END GENERATED:COMMANDS_ROSTER` block in `commands/commands.md` — regenerated by `platform/tooling/sync-commands-catalog.sh`.
  - Any path matched by `.gitignore` (e.g. `projects/`, `extensions/`, `ide_state.json`, `plugins/`, `skills/`, `plans/`, `subagents/`) — runtime state, never source.
- Ownership boundaries:
  - `commands/<ns>/index.md` owns public routing; route bodies belong in `commands/<ns>/<route>/index.md`.
  - `platform/standards/*.md` owns cross-route invariants and standards; routes cite them rather than restating them.
  - `platform/templates/*` is the only source for scaffold files installed by `/agent install`; installed copies in target repos are edited only via `/agent patch` and `/agent upgrade`.
  - `tests/specs/*.md` owns Markdown-layer harness policy; `tests/**/*.test.sh` owns the shell-executable harness.
  - Command-advisory vocabulary: `platform/data/*.json` owns shared policy and schema; a namespace's caller recommendations live at `platform/data/advisories/<ns>.json` (central) or `commands/<ns>/data/<ns>.json` (per-slice — use when the namespace owns a `commands/<ns>/data/` directory, as collab does at `commands/collab/data/collab.json`). `platform/tooling/command-advisories.py` resolves both locations and validates coverage, duplicate sources, and leakage.
  - `platform/tooling/*` and `commands/collab/engine/*` are the only mutators of `generated/*` and the roster block.
  - Each `commands/<ns>/` slice owns: `commands/<ns>/index.md` (namespace router), `commands/<ns>/<route>/index.md` route playbooks (**porcelain** — catalog-dispatched, user-invocable), `commands/<ns>/reference/` cross-route reference documents (**plumbing** — non-dispatchable, not catalog-indexed), `commands/<ns>/engine/` executable backing helpers (**plumbing** — non-dispatchable), and `commands/<ns>/data/` namespace-local data files.
  - `platform/` is shared infrastructure across all namespaces: `platform/standards/` owns cross-namespace invariants and standards; `platform/tooling/` owns executable tooling; `platform/templates/` owns scaffold templates; `platform/data/` owns shared command-advisory policy and schema (per-namespace advisories may live here or in the namespace's own slice).

## 5) Validation Modes

### Source Mode (required)

- `./tests/run.sh`

### Runtime Mode (required if the repo projects runtime state)

This repo projects runtime state under `~/.cursor/*` and generated mirrors under `generated/`. Required validation:

- `./platform/tooling/audit.sh` (includes `audit-role-prose.sh`, `check-source-ledger.py --check`, and `sync-context-gate.sh --check`)
- `./platform/tooling/sync-commands-catalog.sh --check`
- `./platform/tooling/sync-framework-boundaries.sh` (run and diff `generated/` if `--check` is unsupported)
- `./platform/tooling/sync-roles-roster.sh` (run and diff `generated/` if `--check` is unsupported)
- `/test all` (Markdown-harness sweep over `tests/specs/`)

### Overlay Mode (optional)

No project-local overlay is owned by this repo. Consumer repos that carry their own overlay validate it through that repo's own gates; this repo does not gate overlays from upstream.

## 6) Reporting Contract

When work completes, report:

- Each validation command executed and its pass/fail status, including any documented skips with rationale.
- Whether root adapters (`CLAUDE.md`, `AGENTS.md`, `REPOSITORY.md`, `README.md`) and scaffold templates (`platform/templates/*`) were modified.
- Whether any `generated/*` file or the `COMMANDS_ROSTER` block in `commands/commands.md` was regenerated, and which sync script produced the change.
- Any unresolved install or patch placeholder markers remaining in installed scaffold files.
- Any residual risks: known blockers in `tests/specs/*`, deferred test additions, or boundary cases that affected the run.
