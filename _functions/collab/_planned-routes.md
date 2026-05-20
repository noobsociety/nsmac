# Planned-routes gate

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** planned routes, planned route gate, issue bridge prerequisites, validate_planned_route_prerequisites

## Steps

1. Read this document when auditing or changing `tools/collab/planned_routes.py` behavior.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

Spec for `tools/collab/planned_routes.py` — the planned-route prerequisite gate. This module guards against enabling routes that would change the committed workflow model (seal-terminal as default; see `REPOSITORY.md § 10`) before the required contract surface is present in the repository.

### Public entry

`validate_planned_route_prerequisites(cursor_root: Path) -> None`

Called by `tools/collab/registry.py` via `validate_registry()` at load time. Calls the issue-bridge gate with `include_issue_route=True`, meaning the `_functions/git/issue.md` route file is also checked as a prerequisite when the issue bridge is declared.

### Prerequisite semantics

A **planned route** is any route that, if implemented, would activate a non-default workflow model. Detection: the gate inspects `commands/collab.md`, `commands/commands.md`, and the presence of `_functions/collab/export-issues.md` for known identifiers. When a planned route is detected, all named prerequisite artifacts must contain their required substrings before any registry operation proceeds.

**Issue bridge** is the current planned route. Prerequisites:

| Label | Required artifact | Required substring |
|---|---|---|
| `helper-output abort families` | `_functions/collab/_helper-output.md` | `## Abort families` |
| `full-body envelope rejection` | `_functions/collab/_helper-output.md` | `Full-body envelope rejection` |
| `paired-execution-signature double-increment guard` | `_functions/collab/_helper-output.md` | `Paired-execution-signature double-increment guard` |
| `archive protocol violation` | `_functions/collab/_helper-output.md` | `seal-verification-archive-protocol-violation` |
| `logical module annotations` | `_functions/collab/_helper-output.md` | `logical module` (case-insensitive) |
| `rebinding invariant test file` | `tests/tools/collab/registry.py/rebinding-invariants.test.sh` | `#!/usr/bin/env bash` |
| `projectId rebinding coverage` | `tests/tools/collab/registry.py/rebinding-invariants.test.sh` | `projectId rebinding` |
| `participant agentId rebinding coverage` | `tests/tools/collab/registry.py/rebinding-invariants.test.sh` | `agentId rebinding` |
| `issue bridge gate coverage` | `tests/tools/collab/registry.py/rebinding-invariants.test.sh` | `issue bridge` |
| `issue output contract` | `_functions/git/issue.md` | `Output contract` |
| `issue caller-distinction` | `_functions/git/issue.md` | `connector-backed` |
| `issue owner metadata` | `_functions/git/issue.md` | `Owner metadata` |
| `issue requires preservation` | `_functions/git/issue.md` | `_requires:` |
| `issue implement handoff shape` | `_functions/git/issue.md` | `Implement handoff shape` |

### Firing point

Load-time, during `validate_registry()` in `tools/collab/registry.py`. The gate fires before any registry data is returned to the caller, on every registry-loading command.

### Abort family

**Issue bridge blocked**

Fires when the issue bridge is declared (planned route detected) and one or more prerequisite substrings are missing from the required artifacts.

Exit-1 message (exact): `issue bridge blocked until prerequisite artifacts are present: _functions/collab/_helper-output.md and tests/tools/collab/registry.py/rebinding-invariants.test.sh; <issue_clause>missing <labels>`

Where `<issue_clause>` is `third prerequisite: _functions/git/issue.md (output contract); ` when the issue route file is included as a required prerequisite, otherwise empty; and `<labels>` is the comma-space-joined list of missing label names.

**Module-to-subcommand map row:** `planned-route-gates` in `_functions/collab/_helper-output.md`.
