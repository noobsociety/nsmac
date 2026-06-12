# (collab reopen)

Restore a collaboration from a non-success `Completion.verification` verdict to the verdict's routed phase.

## Trigger

**Dispatch:** `(collab reopen <action-plan | handoff> [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab reopen verdict, restore failed seal, verification verdict restore

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If `<phase>` is not `action-plan` or `handoff`, **ABORT**: reopen phase must be one of: action-plan, handoff.
4. If the collab is archived, **ABORT**: record is archived.
5. If the collab is not currently in `Completion`, **ABORT**: `(collab reopen)` is valid only after a non-success Completion verdict.
6. If the verdict is absent or its `outcome` is not `incomplete` or `failed`, **ABORT**: `(collab reopen)` requires a non-success Completion verdict.
7. If the verdict `restoreTarget` does not match `<phase>`, **ABORT**: phase mismatch; name the verdict target and expected token.
8. Call `commands/collab/engine/registry.py reopen <target> <phase> --caller-role <role>` to apply the full reset path.
9. Report the helper output exactly. Stop.

## Notes

- **Parameters:** `<phase>` is `action-plan` or `handoff`. `target` is a collab slug, id, or numeric `#N`; when absent, resolve per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the token after `<phase>` is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Full reset path:** This route wraps `reopen_collab`. It restores status, active phase, active collab pointer, phase turn order, completion execution state, stale seal state, verdict state, and the managed transcript header. It replaces the unsafe `set active-phase --force` recovery path for non-success assessment verdicts.
- **Scope-aware re-verification:** Reopen preserves the completed participant verification of any role whose `handoff.roles.<role>.writeScope` and executed content are both unchanged; only roles you re-scope, or whose execution you re-run, re-verify when the collab advances back into `Completion`. The fresh verification round is earned by those roles' re-runs, so the unchanged roles do not repeat their audit. When no role is re-scoped or re-executed, every role re-verifies — a round must be earned by a real participant completion and cannot be synthesized.
- **Phase mapping:** `action-plan` maps to `Action Plan`; `handoff` maps to `Handoff`.
- **Cap-exit distinction:** `(collab seal verification --cap-exit reopen-handoff)` and `--cap-exit reopen-action-plan` remain direct reviewer cap-exit paths. `(collab reopen)` is for non-success assessment verdicts that already recorded a `restoreTarget`.
- **Coverage carry-forward:** Before clearing execution state, reopen saves current coverage into `reopenCoverage` (`{ createdAt: ISO-8601, executionEntries: object[] }`). At seal time, `valid_carried_execution_entries` re-checks each saved entry against `HEAD`; paths deleted or changed since the snapshot are dropped, surviving paths are merged with the current round's coverage. Do not use `record_execution` to restore prior paths — it replaces the role's full execution row and breaks content-addressing (Invariant #20). See Invariant #21 in [invariants.md](../../../commands/collab/reference/invariants.md) for the full lifecycle.
- **Recovery sequence:** For the full failed-verdict operator path, see [`seal-verification.md` Restore-route recovery](../seal-verification/index.md#restore-route-recovery).

```route-arg
dispatch: (collab reopen <action-plan | handoff> [<target>])
param: name=<action-plan | handoff>; required=required; placeholder=<action-plan | handoff>; class=literal; values=action-plan | handoff
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
