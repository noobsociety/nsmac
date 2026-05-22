# /collab reopen

Restore a collaboration from a non-success `Completion.verification` verdict to the verdict's routed phase.

## Trigger

**Slash:** `/collab reopen`
**Signature:** `/collab reopen <action-plan | handoff> [<target>]`
**Prose dispatch:** `(collab reopen <action-plan | handoff> [<target>])` — prose routing hint; not a terminal command.
**Search phrases:** collab reopen verdict, restore failed seal, verification verdict restore

## Steps

1. Read [_invariants.md](_invariants.md) before executing; call the helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If `<phase>` is not `action-plan` or `handoff`, **ABORT**: reopen phase must be one of: action-plan, handoff.
4. If the collab is archived, **ABORT**: record is archived.
5. If the collab is not currently in `Completion`, **ABORT**: `/collab reopen` is valid only after a non-success Completion verdict.
6. If the verdict is absent or its `outcome` is not `incomplete` or `failed`, **ABORT**: `/collab reopen` requires a non-success Completion verdict.
7. If the verdict `restoreTarget` does not match `<phase>`, **ABORT**: phase mismatch; name the verdict target and expected token.
8. Call `tools/collab/registry.py reopen <target> <phase> --caller-role <role>` to apply the full reset path.
9. Report the helper output exactly. Stop.

## Notes

- **Parameters:** `<phase>` is `action-plan` or `handoff`. `target` is a collab slug, id, or numeric `#N`; when absent, resolve per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the token after `<phase>` is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Full reset path:** This route wraps `reopen_collab`. It restores status, active phase, active collab pointer, phase turn order, completion execution state, stale seal state, verdict state, and the managed transcript header. It replaces the unsafe `set active-phase --force` recovery path for non-success assessment verdicts.
- **Phase mapping:** `action-plan` maps to `Action Plan`; `handoff` maps to `Handoff`.
- **Cap-exit distinction:** `/collab seal verification --cap-exit reopen-handoff` and `--cap-exit reopen-action-plan` remain direct reviewer cap-exit paths. `/collab reopen` is for non-success assessment verdicts that already recorded a `restoreTarget`.
- **Recovery sequence:** For the full failed-verdict operator path, see [`seal-verification.md` Restore-route recovery](seal-verification.md#restore-route-recovery).

```route-arg
dispatch: (collab reopen <action-plan | handoff> [<target>])
param: name=<action-plan | handoff>; required=required; placeholder=<action-plan | handoff>; class=literal; values=action-plan | handoff
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
