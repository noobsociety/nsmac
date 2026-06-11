# /collab open

Reopen a closed collaboration record in the registry when additional discussion or execution is required.

## Trigger

**Slash:** `/collab open`
**Signature:** `/collab open`
**Prose dispatch:** `(collab open)` — prose routing hint; not a terminal command.
**Search phrases:** collab open, reopen collab, reopen collaboration record

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `open`, report that the record is already open and stop.
4. If the collab is archived, **ABORT**: archived records must be restored before reopening.
5. Update the registry status to `open`.
6. Update the Status cell in the transcript state table from `closed` to `open`.
7. Set `activeCollabId` to the reopened collab id.
8. Stop after updating registry and transcript.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `open`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Ownership boundary:** `status` is owned by `open` and `close`. `/collab set` must not change it during normal operation.
- **Read/write ownership:** `records/<slug>.md` (moderator project transcript) is written exclusively by `/collab aggregate` and read by the moderator only. `records/<slug>-raw.md` (raw transcript) is written by lifecycle operations (speak, advance, reopen) and read by agents and participants. The default path gives the moderator the aggregator-written projection. `--raw` gives access to the lifecycle-written file; see **`--raw` flag** below.
<!-- abort: open-raw-default -->
- **`--raw` flag:** When the route is invoked with `--raw`, it renders the raw transcript (`records/<slug>-raw.md`) directly instead of the moderator project transcript (`records/<slug>.md`). `records/<slug>-raw.md` is the lifecycle-written file — populated by speak, advance, and reopen operations. **ABORT** (agent-honor-system): Do not use `--raw` as a default or routine invocation flag. `--raw` bypasses reader separation — the design boundary that protects the moderator's polished view from unformatted contribution noise. Use `--raw` only when explicitly diagnosing a rendering issue or when directed by a moderator. Normal moderator viewing must use the default path (without `--raw`), which renders the moderator project transcript.
