# (collab close)

Mark a collaboration record closed so contribution and phase-advance routes stop writing to it.

## Trigger

**Dispatch:** `(collab close [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab close, close collaboration, end collab record

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed`, report that the record is already closed and stop.
4. Ask: would any durable rationale in the current transcript (Audit-block content, reviewer findings, seal-trust caveats, or qualifications) be lost if the transcript were not in context? If yes and the rationale belongs in committed source, promote it now — write it into the relevant route doc, reference doc, or invariant file and commit — before closing. If promotion is out of scope for this close, file a concrete backlog row naming the slug, file, and exact location before closing. If no source-worthy rationale is found, state that explicitly and continue.
5. Call `commands/collab/engine/registry.py close <target>` to: Update the registry status to `closed`. Update the Status cell in the transcript state table from `open` to `closed`. If the closing collab id matches `activeCollabId`, clear `activeCollabId`. Do not change the active pointer when it selects a different collab. When the managed header changes, the helper prints `HEADER-OVERWRITE:` first; the next line is `NEXT: Collab closed; run /clear before starting another collab.`
6. Display the `NEXT:` line and clear notice emitted by the `close` helper after the status change completes.
7. Stop after changing the registry status, transcript status, active-pointer cleanup, and the clear notice display.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `close`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Promotion-discipline context:** Step 4 addresses a qualitative gap that the structured-field rules in `invariants.md` and `platform/data/doctrines.md` do not cover: collab-specific reasoning such as Audit-block content, reviewer findings, and seal-trust caveats can encode general principles that belong in committed source, but no close-time surface prompted that check before this step was added. The enforcement is a route-doc test guarding against silent removal rather than a `charteredDeliverables` binding, because the check is qualitative human judgment rather than the presence of a committed file. See the **Promotion mechanism** note in [`seal-verification/index.md`](../seal-verification/index.md) for the full rationale.
- **Active cleanup:** Clearing `activeCollabId` means leaving the registry pointer empty. Subsequent routes must refuse target inference until the moderator runs `(collab activate <record>)` or names a target explicitly.
- **No summary emission:** `close` does not write, modify, or require a `### Summary —` block, and does not accept a `--no-summary` flag — no such flag exists. Automatic close-summary generation happens only via `(collab run plan)`'s auto-close path, when execution recording closes the collab and no summary exists yet; see [`run-plan/index.md`](../run-plan/index.md).
- **Tag boundary:** Close is a lifecycle-state transition and notification surface only. It must not call `commands/collab/engine/registry.py tag`, `git push`, pull-request creation, direct merge, GitHub release creation, or changelog generation. Use `(collab tag)` explicitly after the collab has reached the required tag point.
- **Closed-record behavior:** `(collab speak)` and `(collab advance)` must refuse closed records.
- **Clear notice:** After closing, the helper's `NEXT:` line reads `Collab closed; run /clear before starting another collab.`, followed by an `EFFICIENCY:` line, the collab id, and the trailing lifecycle notice. By default (no `--json`) that notice renders as the single line `NOTICE: Run /clear before starting another collab.`; pass `--json` to receive the structured `{"notice": "clear", "status": "closed", "message": "..."}` record instead — shape owned by [invariants.md](../../../commands/collab/reference/invariants.md) Note 3. Display the `NEXT:` line and the trailing notice to the caller. Route docs describe the output; they do not reimplement it.
- **Post-state resume signal:** After `(collab close)` the collab is closed and `activeCollabId` is cleared. Run `/clear` before starting a new collab. No `speak-state --resume` applies — the closed record is no longer active.
- **Sync contract compliance:** Step 5's registry-status and transcript Status-cell updates are written together by the single `close` helper call named in that Step, satisfying the sync contract's Helper-rendered form.

```route-arg
dispatch: (collab close [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
