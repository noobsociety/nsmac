# (collab open)

Reopen a closed collaboration record in the registry when additional discussion or execution is required.

## Trigger

**Dispatch:** `(collab open)` — routing-only command form; not a shell command.
**Search phrases:** collab open, reopen collab, reopen collaboration record

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `open`, report that the record is already open and stop.
4. If the collab is archived, **ABORT**: archived records must be restored before reopening.
5. Call `commands/collab/engine/registry.py open <target>` to update the registry status to `open`.
6. Update the Status cell in the transcript state table from `closed` to `open`.
7. Set `activeCollabId` to the reopened collab id.
8. Stop after updating registry and transcript.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `open`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Ownership boundary:** `status` is owned by `open` and `close`. `(collab set)` must not change it during normal operation.
- **Read/write ownership:** `records/<slug>.md` (lifecycle transcript) is written by lifecycle operations (speak, advance, reopen) and read by agents, participants, and the moderator alike. The single transcript is the authoritative collab record; no separate moderator-facing view exists.
