# /collab open

Reopen a closed collaboration record in the registry when additional discussion or execution is required.

## Trigger

**Slash:** `/collab open`
**Signature:** `/collab open`
**Prose dispatch:** `(collab open)` — prose routing hint; not a terminal command.
**Search phrases:** collab open, reopen collab, reopen collaboration record

## Steps

1. Read [_invariants.md](_invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `open`, report that the record is already open and stop.
4. If the collab is archived, **ABORT**: archived records must be restored before reopening.
5. Update the registry status to `open`.
6. Update the Status cell in the transcript state table from `closed` to `open`.
7. Set `activeCollabId` to the reopened collab id.
8. Stop after updating registry and transcript.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `open`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Ownership boundary:** `status` is owned by `open` and `close`. `/collab set` must not change it during normal operation.
