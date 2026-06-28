# (collab close)

Mark a collaboration record closed so contribution and phase-advance routes stop writing to it.

## Trigger

**Dispatch:** `(collab close [--no-summary])` — routing-only command form; not a shell command.
**Search phrases:** collab close, close collaboration, end collab record

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
<!-- abort: close-record-unreadable -->
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed`, report that the record is already closed and stop.
4. Ask: would any durable rationale in the current transcript (Audit-block content, reviewer findings, seal-trust caveats, or qualifications) be lost if the transcript were not in context? If yes and the rationale belongs in committed source, promote it now — write it into the relevant route doc, reference doc, or invariant file and commit — before closing. If promotion is out of scope for this close, file a concrete backlog row naming the slug, file, and exact location before closing. If no source-worthy rationale is found, state that explicitly and continue.
5. Call `commands/collab/engine/registry.py close <target>` to: Update the registry status to `closed`. Update the Status cell in the transcript state table from `open` to `closed`. If the closing collab id matches `activeCollabId`, clear `activeCollabId`. Do not change the active pointer when it selects a different collab. The first output line is `NEXT: Collab closed; run /clear before starting another collab.`
6. Call `(collab rewrite summary)` to add narrative refinement to the structural `### Summary —` block emitted by the helper.
7. Display the `NEXT:` line and clear notice emitted by the `close` helper after the status change completes.
8. Stop after changing the registry status, transcript status, active-pointer cleanup, any summary, and the clear notice display.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `close`; when absent, resolved per **Registry targeting** in **Notes**. `--no-summary` — skip the automatic summary (optional).
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric `#N` position. Otherwise use `activeCollabId`.
<!-- abort: close-registry-target-unavailable -->
  If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Promotion-discipline context:** Step 4 addresses a qualitative gap that the structured-field rules in `invariants.md` and `platform/data/doctrines.md` do not cover: collab-specific reasoning such as Audit-block content, reviewer findings, and seal-trust caveats can encode general principles that belong in committed source, but no close-time surface prompted that check before this step was added. The enforcement is a route-doc test guarding against silent removal rather than a `charteredDeliverables` binding, because the check is qualitative human judgment rather than the presence of a committed file. See the **Promotion mechanism** note in [`seal-verification/index.md`](../seal-verification/index.md) for the full rationale.
- **Active cleanup:** Clearing `activeCollabId` means leaving the registry pointer empty. Subsequent routes must refuse target inference until the moderator runs `(collab activate <record>)` or names a target explicitly.
- **Summary default:** The `close` helper emits a structural `### Summary —` block automatically; no route-level generation step is required. Pass `--no-summary` to skip narrative refinement. Use `(collab rewrite summary)` on closed records to replace the narrative body.
- **Summary-emission invariant:** A `### Summary —` block is written to `## Completion` at close; no follow-up step is required.
- **Closed-record behavior:** `(collab speak)` and `(collab advance)` must refuse closed records.
- **Clear notice:** The helper emits `NEXT: Collab closed; run /clear before starting another collab.` as the first output line and `{"message": "Run /clear before starting another collab.", "notice": "clear", "status": "closed"}` after closing. Display both to the caller. Route docs describe the output; they do not reimplement it. See [invariants.md](../../../commands/collab/reference/invariants.md).
- **Post-state resume signal:** After `(collab close)` the collab is closed and `activeCollabId` is cleared. Run `/clear` before starting a new collab. No `speak-state --resume` applies — the closed record is no longer active.
- **Sync contract compliance:** Step 6's narrative refinement call (`(collab rewrite summary)`) is prose-rendered. The structural summary is helper-owned and does not require a sync-contract declaration. The exception is declared under the sync contract in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md).

```route-arg
dispatch: (collab close [--no-summary])
param: name=--no-summary; required=optional; placeholder=--no-summary; class=literal; values=present; default=literal:false
```
