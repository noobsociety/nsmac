# (collab restore)

Move the active phase back by one step in a collaboration record when the moderator needs more work in an earlier phase.

## Trigger

**Dispatch:** `(collab restore)` — routing-only command form; not a shell command.
**Search phrases:** collab prev, previous collaboration phase, rollback collab phase

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
<!-- abort: restore-record-unreadable -->
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
<!-- abort: restore-record-is-closed -->
3. If the registry status is `closed` or `archived`, **ABORT**: record is closed.
<!-- abort: restore-active-phase-missing -->
4. Resolve the current phase from registry `activePhase`. If missing or unknown, **ABORT**: active phase missing in metadata.
<!-- abort: restore-no-previous-phase -->
5. Resolve the previous phase from **Phase sequence** in **Notes**. If no previous phase exists, **ABORT**: no previous phase; sequence exhausted.
6. Update registry `activePhase` to the previous phase by calling `commands/collab/engine/registry.py advance <target> prev`; the helper also renders the transcript status table from the resulting registry state.
7. Confirm the helper recomputed `turnOrder` for the restored phase from participants and phase context. Moderator-included phases (`Audit`, `Discussion`) restore the moderator to the front of the order; moderator-excluded phases (`Conclusion`, `Action Plan`, `Handoff`, `Completion`) keep the moderator out; the reviewer is never placed in `turnOrder` directly.
8. Confirm the helper-updated Active phase cell in the transcript state table names the previous phase.
9. Stop after the helper updates registry and transcript. Never delete or rewrite existing contributions.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `restore`; when absent, resolved per **Registry targeting** in **Notes**.
<!-- abort: restore-registry-target-unavailable -->
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Phase sequence:** `Audit` <- `Discussion` <- `Conclusion` <- `Action Plan` <- `Handoff` <- `Completion`.
- **Multi-phase rollback:** For rollbacks spanning more than one phase, use `(collab set active-phase <phase> --force)` directly rather than chaining sequential calls; this is the canonical batch rollback path.
- **Append-only rollback:** `(collab restore)` moves only the active-phase pointer. `(collab restore)` never removes headings, contributions, checklist items, or completion markers.
<!-- abort: restore-helper-mirror-defect -->
- **Recovery path:** If `commands/collab/engine/registry.py advance <target> prev` returns without the expected registry phase, restored turn order, or transcript status table change, **ABORT** (agent-honor-system): treat the missing mirror as a helper defect and do not hand-edit the status table except through a dedicated repair route.
- **Post-state resume signal:** After `(collab restore)` completes, re-establish collab context with `commands/collab/engine/registry.py speak-state --resume <target> <role>` before writing the next contribution.
- **Sync contract compliance:** `commands/collab/engine/registry.py advance prev` owns registry phase, turn-order restoration, and status-table rendering. No restore-path prose-rendered write is expected; any missing mirror is a helper defect under the sync contract in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md).
