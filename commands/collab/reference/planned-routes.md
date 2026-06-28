# Planned-routes gate

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** planned routes, planned route gate, issue bridge prerequisites, validate_planned_route_prerequisites

## Steps

1. Read this document when auditing or changing `commands/collab/engine/planned_routes.py` behavior.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The spec covers `commands/collab/engine/planned_routes.py` — the planned-route prerequisite gate. The module guards against enabling routes that would change the committed workflow model (seal-terminal as default; see [`workflow-models.md` § Committed workflow model](workflow-models.md#committed-workflow-model); see also [`REPOSITORY.md` § Collab Workflow Models](../../../REPOSITORY.md#6-collab-workflow-models)) before the required contract surface is present in the repository.

**Current issue-terminal status:** active and tested. The issue bridge
prerequisites are present, `--terminal issue` is selectable, and
`tests/commands/collab/registry.py/export-issues-flow.test.sh` proves
`(collab export-issues)` closes an issue-terminal collab end to end after
execution evidence and issue handoff evidence are recorded. Beyond the close
flow, `export-issues` ABORT-clause coverage is now anchored and tested: each
guard carries a stable `<!-- abort: export-issues-... -->` anchor with a matching
P9 test for the six helper-enforced guards, and the step-2 record-unreadable
clause is marked `(agent-honor-system)`.

### Public entry

`validate_planned_route_prerequisites(config_root: Path) -> None`

Called by `commands/collab/engine/registry_validation.py` via `validate_registry()` at load time. Calls the issue-bridge gate with `include_issue_route=True`, meaning the `commands/git/issue/index.md` route file is also checked as a prerequisite when the issue bridge is declared.

### Prerequisite semantics

A **planned route** is any route that, if implemented, would activate a non-default workflow model. Detection: the gate inspects `commands/collab/index.md`, `commands/commands.md`, and the presence of `commands/collab/export-issues/index.md` for known identifiers. When a planned route is detected, all named prerequisite artifacts must contain their required substrings before any registry operation proceeds.

**Issue bridge** is the current planned route. Prerequisites:

| Label | Required artifact | Required substring |
|---|---|---|
| `helper-output abort families` | `commands/collab/reference/helper-output.md` | `## Abort families` |
| `full-body envelope rejection` | `commands/collab/reference/helper-output.md` | `Full-body envelope rejection` |
| `paired-execution-signature double-increment guard` | `commands/collab/reference/helper-output.md` | `Paired-execution-signature double-increment guard` |
| `archive protocol violation` | `commands/collab/reference/helper-output.md` | `seal-verification-archive-protocol-violation` |
| `logical module annotations` | `commands/collab/reference/helper-output.md` | `logical module` (case-insensitive) |
| `rebinding invariant test file` | `tests/commands/collab/registry.py/rebinding-invariants.test.sh` | `#!/usr/bin/env bash` |
| `projectId rebinding coverage` | `tests/commands/collab/registry.py/rebinding-invariants.test.sh` | `projectId rebinding` |
| `participant agentId rebinding coverage` | `tests/commands/collab/registry.py/rebinding-invariants.test.sh` | `agentId rebinding` |
| `issue bridge gate coverage` | `tests/commands/collab/registry.py/rebinding-invariants.test.sh` | `issue bridge` |
| `issue output contract` | `commands/git/issue/index.md` | `Output contract` |
| `issue caller-distinction` | `commands/git/issue/index.md` | `connector-backed` |
| `issue owner metadata` | `commands/git/issue/index.md` | `Owner metadata` |
| `issue requires preservation` | `commands/git/issue/index.md` | `_requires:` |
| `issue implement handoff shape` | `commands/git/issue/index.md` | `Implement handoff shape` |

### Firing point

Load-time, during `validate_registry()` in `commands/collab/engine/registry_validation.py`. The gate fires before any registry data is returned to the caller, on every registry-loading command.

### Abort family

**Issue bridge blocked**

Fires when the issue bridge is declared (planned route detected) and one or more prerequisite substrings are missing from the required artifacts.

Exit-1 message (exact): `issue bridge blocked until prerequisite artifacts are present: commands/collab/reference/helper-output.md and tests/commands/collab/registry.py/rebinding-invariants.test.sh; <issue_clause>missing <labels>`

Where `<issue_clause>` is `third prerequisite: commands/git/issue/index.md (output contract); ` when the issue route file is included as a required prerequisite, otherwise empty; and `<labels>` is the comma-space-joined list of missing label names.

**Module-to-subcommand map row:** `planned-route-gates` in `commands/collab/reference/helper-output.md`.

## Current gate status

**Issue bridge prerequisites: PASS** as of 2026-06-24 (structural-architecture-completion-audit). All 15 prerequisite substrings are present; `validate_planned_route_prerequisites` exits without error. Issue-terminal is active: `--terminal issue` is a selectable value at init time, and `(collab export-issues)` closes a collab end-to-end. End-to-end proof: `tests/commands/collab/registry.py/issue-terminal-close-flow.test.sh` and `tests/commands/collab/registry.py/export-issues-flow.test.sh`. Beyond the close flow, `export-issues` ABORT coverage is anchored and tested per-guard; the only non-tested clause is the step-2 record-unreadable guard, marked `(agent-honor-system)`. This section should be updated whenever the gate status changes.
