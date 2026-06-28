# (collab export-issues)

Record exported issue handoff evidence for an issue-terminal collaboration record.

## Trigger

**Dispatch:** `(collab export-issues <evidence-file>)` — routing-only command form; not a shell command.
**Search phrases:** collab export issues, issue terminal evidence, exported issue handoff

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
<!-- abort: export-issues-record-unreadable -->
2. Read the resolved registry and transcript. If either is unreadable, **ABORT** (agent-honor-system): record unreadable; name the path. The `export-issues` helper reads the registry but performs no up-front transcript read before its lifecycle guards (status, phase, terminal, role, participant, execution); the transcript is only touched on the close path after every guard has passed. No mirrored helper guard raises a transcript-unreadable abort at this step, so the read precondition is honor-system.
<!-- abort: export-issues-record-closed -->
3. If the registry status is `closed` or `archived`, **ABORT**: collab is closed or archived; cannot export issues.
<!-- abort: export-issues-role-not-pe -->
4. Resolve the executing role from the registry participants list. The exporting role must be `pe`; otherwise **ABORT**: issue export must be authored by platform engineer role pe.
<!-- abort: export-issues-phase-not-completion -->
5. If the active phase is not `Completion`, **ABORT**: `(collab export-issues)` is valid only in `Completion`.
<!-- abort: export-issues-terminal-not-issue -->
6. If the stored `terminal` is not `issue`, **ABORT**: `(collab export-issues)` requires terminal issue.
<!-- abort: export-issues-pending-execution -->
7. If any non-moderator assigned role lacks a completed execution entry, **ABORT**: issue export blocked: pending execution role(s) remain.
8. Read `<evidence-file>` as JSON. The file must contain an `issues` array with at least one object. Each issue object must contain non-empty `title`; optional `url`, `body`, `owner`, and `delivery` fields must be non-empty strings when present; optional `requires` must be a list of non-empty strings.
9. Call `commands/collab/engine/registry.py export-issues <target> pe --evidence-file <evidence-file> --caller-role pe`.
10. Report the helper's `NEXT:` advisory, registry status, and whether the close notice was emitted.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `export-issues`; when absent, resolved per **Registry targeting** in **Notes**. `<evidence-file>` is a local JSON file carrying exported issue handoff evidence.
<!-- abort: export-issues-registry-target -->
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present and the next token is not an existing file path, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Evidence contract:** The helper records `exportedIssues = { exportedAt, exportedBy, issues }` in the registry. The field is the durable replacement close-gate for issue-terminal records.
- **Close behavior:** When exported issue handoff evidence is recorded and all non-moderator assigned execution roles are complete, the helper closes the record, clears `activeCollabId` when it points at the collab, updates the transcript header status, and writes the default Completion summary when one is absent.
- **Seal boundary:** The route must not write `verificationSeal` and must not enter `Completion.verification`. Issue-terminal close is governed by exported issue handoff evidence, not reviewer seal state.

```route-arg
dispatch: (collab export-issues <evidence-file>)
param: name=<evidence-file>; required=required; placeholder=<evidence-file>; class=type; rule=JSON issue export evidence path
```
