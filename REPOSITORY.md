# Repository contract

Contract between this repository (source plane) and the global agent runtime at `~/.cursor/*`.

## 1) System model

The contract has three planes:

- **Source plane:** version-controlled files in this repository.
- **Global runtime plane:** `~/.cursor/*`.
- **Project overlay plane:** optional project-local overlay.

Only the source plane is authoritative. Runtime planes are derived execution contexts.

## 2) Authority chain

Authority is strict and ordered:

1. Repo-owned executable checks and scripts:
   - `./tests/run.sh` (runs `./platform/tooling/audit.sh` then the retained test manifest)
   - `./platform/tooling/audit.sh` (adapter routing, runtime ignore rules, role-key prose drift guard)
   - `./platform/tooling/sync-context-gate.sh --check` (context-gate canonical source shape: present, no frontmatter, at least one critical directive retained)
   - `./platform/tooling/audit-role-prose.sh` (role-key prose drift guard for Markdown and MDC surfaces)
   - `./platform/tooling/sync-commands-catalog.sh --check` (commands roster integrity)
   - `./platform/tooling/sync-framework-boundaries.sh` (framework boundary projections)
   - `./platform/tooling/sync-roles-roster.sh` (roles roster projection)
   - `./platform/tooling/audit-collab-route-wiring.py` (run by `audit.sh`; every public collab route resolves to a backing `registry.py` helper subcommand — catalogued routes stay wired, no documented-but-unbacked surface)
   - `./platform/tooling/audit-collab-readonly-contract.py` (run by `audit.sh`; every collab route doc that claims read-only calls only non-mutating `registry.py` subcommands)
   - `./platform/tooling/audit-deleted-path-references.py` (run by `audit.sh`; tracked source does not reference files that are absent at `HEAD` after deletion in git history)
   - `./platform/tooling/audit-doc-paths.py` (run by `audit.sh`; backticked repo-relative paths in tracked Markdown resolve — only deliberately-prohibited names are allowlisted)
   - `./platform/tooling/audit-present-state.py` (run by `audit.sh`; tracked source carries present state only, with no past/future outcome residue)
   - The list above names the load-bearing checks; `./platform/tooling/audit.sh` runs the complete, authoritative set — including topology, placement, reachability, vocabulary, advisory, and behavior-smoke-floor (`check_behavior_smoke_floor`) checks not separately enumerated here.
**Execution prerequisites** for the checks listed above are specified in [`platform/standards/runtime-contract.md`](platform/standards/runtime-contract.md): Python ≥ 3.9, bash ≥ 3.2, `git` and `python3` on `$PATH`, and stdlib-only Python tooling.

`./platform/tooling/coverage-gate.sh` proves the mandatory behavior-smoke floor and reports opt-in per-clause coverage over public collab routes in `commands/collab/`. The floor is mandatory for every route; per-clause ABORT coverage — a stable `<!-- abort: <route>-<id> -->` anchor plus a matching P9 test — is opt-in, kept only for the reviewer-selected keep-list rather than required for every discovered ABORT clause. An anchor always means "tested": strip an anchor when its backing test retires, and keep an anchor only while its test remains on the keep-list. Guards that are discipline-only rather than helper-enforced use `agent-honor-system` as the sole vocabulary; no other escape term exists. The retired per-batch burn-down schedule and clause classification live in [`platform/tooling/coverage-gate-migration.md`](platform/tooling/coverage-gate-migration.md).

`tests/commands/collab/registry.py/real-record-behavior-smoke.test.sh` is the mandatory behavior-smoke floor; exercised via `./tests/run.sh`, it asserts the `speak-render` → `speak-state`/lifecycle round trip over live-shaped state built by real helpers in an isolated `COLLAB_STATE_HOME`, demonstrating RED on a desynchronized registry/transcript and GREEN on a valid round trip. The rest of `tests/commands/collab/registry.py/` is the opt-in per-clause keep-list described above. `./platform/tooling/audit.sh` asserts this floor file exists (`check_behavior_smoke_floor`), so deleting it fails the audit rather than silently disabling the floor.

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
   - Ignored runtime state (not source): agent runtime directories, tracking payloads, `argv.json`, `projects/`, `extensions/`, `ide_state.json`, `plugins/`, `skills/`, `plans/`, `subagents/`, and legacy host skill-cache payloads

## 3) Output chain contract

The repo projects the following root outputs, with deepest dependency chains and validation:

- **Adapter routing surface** — `CLAUDE.md`, `AGENTS.md` route into `commands/commands.md` → `commands/<ns>/index.md` → `commands/<ns>/<route>/index.md`, with cross-references into `platform/standards/*.md`. Validated by `./platform/tooling/audit.sh` and the Markdown harness via `(test commands)` and `(test core)`.
- **Generated mirrors** — `generated/collab-lifecycle.md`, `generated/command-reference.md`, `generated/content-invariants.tsv`, `generated/registry-cli.md` are derived from `commands/*`, `commands/collab/reference/*`, central advisory files under `platform/data/advisories/*.json`, and per-slice advisory files under `commands/<ns>/data/<ns>.json` such as `commands/collab/data/collab.json`. Regenerated through `commands/collab/engine/lifecycle-doc.py`, `platform/tooling/command-reference.py`, `platform/tooling/sync-framework-boundaries.sh`, and `commands/collab/engine/registry.py registry-cli-doc`.
- **Collab support contracts** — helper output, identity binding, planned-route gates, registry-state rules, and workflow-model doctrine live in [`helper-output.md`](commands/collab/reference/helper-output.md), [`identity-contract.md`](commands/collab/reference/identity-contract.md), [`planned-routes.md`](commands/collab/reference/planned-routes.md), [`registry-state.md`](commands/collab/reference/registry-state.md), and [`workflow-models.md`](commands/collab/reference/workflow-models.md).
- **Commands roster block** — the `BEGIN GENERATED:COMMANDS_ROSTER` block in `commands/commands.md` is derived from filesystem state under `commands/`. Validated by `./platform/tooling/sync-commands-catalog.sh --check`.
- **Scaffold templates for downstream repos** — `platform/templates/{CLAUDE,AGENTS,REPOSITORY}.md` are copied into target repos by `(agent install)` and patched in place by `(agent patch)`. Validated by `tests/platform/agent/agent-routes-contract.test.sh`.
- **QA harness surface** — `tests/specs/*.md` and `tests/**/*.test.sh` are the executable proof layer. Validated by `(test all)` and `./tests/run.sh`.

## 4) Mutation protocol and ownership

- Must edit tracked source only.
- Do not edit by hand:
  - Files under `generated/` — regenerated by `commands/collab/engine/lifecycle-doc.py`, `platform/tooling/command-reference.py`, `platform/tooling/sync-framework-boundaries.sh`, and `commands/collab/engine/registry.py registry-cli-doc` (for `generated/registry-cli.md`).
  - The `BEGIN GENERATED:COMMANDS_ROSTER` ... `END GENERATED:COMMANDS_ROSTER` block in `commands/commands.md` — regenerated by `platform/tooling/sync-commands-catalog.sh`.
  - Any path matched by `.gitignore` (e.g. agent runtime directories, tracking payloads, `argv.json`, `projects/`, `extensions/`, `ide_state.json`, `plugins/`, `skills/`, `plans/`, `subagents/`) — runtime state, never source.
- Ownership boundaries:
  - `commands/<ns>/index.md` owns public routing; route bodies belong in `commands/<ns>/<route>/index.md`.
  - `platform/standards/*.md` owns cross-route invariants and standards; routes cite them rather than restating them.
  - `platform/templates/*` is the only source for scaffold files installed by `(agent install)`; installed copies in target repos are edited only via `(agent patch)` and `(agent upgrade)`.
  - `tests/specs/*.md` owns Markdown-layer harness policy; `tests/**/*.test.sh` owns the shell-executable harness.
  - Command-advisory vocabulary: `platform/data/*.json` owns shared policy and schema; a namespace's caller recommendations live at `platform/data/advisories/<ns>.json` (central) or `commands/<ns>/data/<ns>.json` (per-slice — use when the namespace owns a `commands/<ns>/data/` directory, as collab does at `commands/collab/data/collab.json`). `platform/tooling/command-advisories.py` resolves both locations and validates coverage, duplicate sources, and leakage.
  - `platform/tooling/*` and `commands/collab/engine/*` are the only mutators of `generated/*` and the roster block.
  - Each `commands/<ns>/` slice owns: `commands/<ns>/index.md` (namespace router), `commands/<ns>/<route>/index.md` route playbooks (**porcelain** — catalog-dispatched, user-invocable), `commands/<ns>/reference/` cross-route reference documents (**plumbing** — non-dispatchable, not catalog-indexed), `commands/<ns>/engine/` executable backing helpers (**plumbing** — non-dispatchable), and `commands/<ns>/data/` namespace-local data files.
  - `platform/` is shared infrastructure across all namespaces: `platform/standards/` owns cross-namespace invariants and standards; `platform/tooling/` owns executable tooling; `platform/templates/` owns scaffold templates; `platform/data/` owns shared command-advisory policy and schema (per-namespace advisories may live here or in the namespace's own slice).

## 5) Validation modes

### Source mode (required)

- `./tests/run.sh`

### Runtime mode (required if the repo projects runtime state)

The repo projects runtime state under `~/.cursor/*` and generated mirrors under `generated/`. Required validation:

- `./platform/tooling/audit.sh` (includes `audit-role-prose.sh`, `sync-context-gate.sh --check`, `audit-collab-route-wiring.py`, `audit-collab-readonly-contract.py`, `audit-deleted-path-references.py`, `audit-doc-paths.py`, and `audit-present-state.py`)
- `./platform/tooling/sync-commands-catalog.sh --check`
- `./platform/tooling/sync-framework-boundaries.sh` (run and diff `generated/` if `--check` is unsupported)
- `./platform/tooling/sync-roles-roster.sh` (run and diff `generated/` if `--check` is unsupported)
- `(test all)` (Markdown-harness sweep over `tests/specs/`)

### Overlay mode (optional)

No project-local overlay is owned by this repo. Consumer repos that carry their own overlay validate it through that repo's own gates; this repo does not gate overlays from upstream.

## 6) Collab workflow model

The committed workflow model is specified in [`commands/collab/reference/workflow-models.md`](commands/collab/reference/workflow-models.md). Reviewer-backed collabs close through execution completion, participant verification, a current reviewer seal, and a success verdict. All close-path logic in `commands/collab/engine/registry.py` and related helpers is downstream of that specification.

## 7) Reporting contract

When work completes, report:

- Each validation command executed and its pass/fail status, including any documented skips with rationale.
- Whether root adapters (`CLAUDE.md`, `AGENTS.md`, `REPOSITORY.md`, `README.md`) and scaffold templates (`platform/templates/*`) were modified.
- Whether any `generated/*` file or the `COMMANDS_ROSTER` block in `commands/commands.md` was regenerated, and which sync script produced the change.
- Any unresolved install or patch placeholder markers remaining in installed scaffold files.
- Any residual risks: known blockers in `tests/specs/*`, deferred test additions, or boundary cases that affected the run.
