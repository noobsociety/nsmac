# Role prohibitions

Reference inventory for role-local advisory prohibitions. The file is prose documentation only; helpers do not parse it and role JSON remains the machine-readable metadata source.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab role prohibitions, moderator prohibitions, role-local advisory constraints

## Steps

1. Read this document when changing role-local advisory prohibition text or reviewing moderator command boundaries.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The inventories below list mutating commands and the prohibited behaviors for each role.

## Moderator mutating-command inventory

- `init` — do not treat the free-text collab title as work to execute.
- `join` — do not change participant role substance beyond registry-backed roster updates.
- `speak` — do not draft, summarize, or expand moderator-supplied message substance.
- `retract speak` — do not reinterpret the retracted contribution while preserving the audit trail.
- `rewrite speak` — do not alter moderator-authored substance beyond the requested rewrite target.
- `advance` — do not use phase movement to introduce new action content.
- `restore` — do not use rollback to delete or obscure prior contribution history.
- `set` — do not use metadata changes to perform source edits or other non-collab work.
- `unset` — do not clear metadata as a substitute for resolving recorded state.
- `close` — do not close while assigned execution state or transcript cleanup remains unresolved.
- `archive` — do not archive as a way to bypass completion or validation.
- `delete` — do not delete records unless the route's destructive-delete guard is satisfied.
- `remove participant` — do not remove participants to bypass turn, reviewer, or execution obligations.
- `write summary` — do not invent or transform moderator message substance.
- `rewrite summary` — do not rewrite summary content beyond the requested correction.
- `run plan` — do not execute non-collab work while acting as moderator.
- `rewrite execution` — do not rewrite execution history to mask failed validation.

## Reviewer mutating-command inventory

- `seal verification` — do not mutate seal-block fields (`executionEntries`, `validationScopes`, `touchedPaths`, `observedRevision`) once `verification.subState == assessment`; only verdict fields (`outcome`, `restoreTarget`, `restoreReason`, `evidence`, `failureCategory`, `nullResult`) may be written during assessment. Once assessment is open, retroactive alteration of the seal block is prohibited; violations are rejected by the helper.
- `seal verification` — do not author `evidence` content beyond read-only anchors (transcript ids, registry revision, committed paths, execution entry ids); implementation steps, command output, and replacement content belong to participants after restore.

