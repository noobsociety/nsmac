# /collab close

Mark a collaboration record closed so contribution and phase-advance routes stop writing to it.

## Trigger

**Slash:** `/collab close`
**Signature:** `/collab close [--no-summary]`
**Prose dispatch:** `(collab close ...)` — prose routing hint; not a terminal command.
**Search phrases:** collab close, close collaboration, end collab record

## Steps

1. Read [invariants.md](../../../core/collab/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed`, report that the record is already closed and stop.
4. Call `tools/collab/registry.py close <target>` to: Update the registry status to `closed`. Update the Status cell in the transcript state table from `open` to `closed`. If the closing collab id matches `activeCollabId`, clear `activeCollabId`. Do not change the active pointer when it selects a different collab. The first output line is `NEXT: Collab closed; run /clear before starting another collab.`
5. Call `/collab rewrite summary` to add narrative refinement to the structural `### Summary —` block emitted by the helper.
6. Display the `NEXT:` line and clear notice emitted by the `close` helper after the status change completes.
7. Stop after changing the registry status, transcript status, active-pointer cleanup, any summary, and the clear notice display.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `close`; when absent, resolved per **Registry targeting** in **Notes**. `--no-summary` — skip the automatic summary (optional).
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric `#N` position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Active cleanup:** Clearing `activeCollabId` means leaving the registry pointer empty. Subsequent routes must refuse target inference until the moderator runs `/collab activate <record>` or names a target explicitly.
- **Summary default:** The `close` helper emits a structural `### Summary —` block automatically; no route-level generation step is required. Pass `--no-summary` to skip narrative refinement. Use `/collab rewrite summary` on closed records to replace the narrative body.
- **Summary-emission invariant:** A `### Summary —` block is written to `## Completion` at close; no follow-up step is required.
- **Closed-record behavior:** `/collab speak` and `/collab advance` must refuse closed records.
- **Clear notice:** The helper emits `NEXT: Collab closed; run /clear before starting another collab.` as the first output line and `{"message": "Run /clear before starting another collab.", "notice": "clear", "status": "closed"}` after closing. Display both to the caller. Route docs describe the output; they do not reimplement it. See [invariants.md](../../../core/collab/invariants.md).
- **Post-state resume signal:** After `/collab close` the collab is closed and `activeCollabId` is cleared. Run `/clear` before starting a new collab. No `speak-state --resume` applies — the closed record is no longer active.
- **Sync contract compliance:** Step 5's narrative refinement call (`/collab rewrite summary`) is prose-rendered. The structural summary is helper-owned and does not require a sync-contract declaration. This is declared under the sync contract in [`core/framework/route-invariant.md`](../../../core/framework/route-invariant.md).

```route-arg
dispatch: (collab close [--no-summary])
param: name=--no-summary; required=optional; placeholder=--no-summary; class=literal; values=present; default=literal:false
```
