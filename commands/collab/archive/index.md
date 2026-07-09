# (collab archive)

Soft-delete a collab by marking it archived so it is preserved on disk but excluded from active routing.

## Trigger

**Dispatch:** `(collab archive [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab archive, archive collab, soft-delete collab record

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is already `archived`, report that the record is already archived and stop.
4. Set registry status to `archived` and `archived` to `true`.
5. If the archiving collab id matches `activeCollabId`, clear `activeCollabId`. Do not change the active pointer when it selects a different collab.
6. Display the clear notice emitted by the helper after the status change completes.
7. Stop after registry cleanup and the clear notice display. Do not move or delete the transcript file.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `archive`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Soft delete:** `archive` marks the record inactive without touching the transcript file. The record remains on disk for auditability and recovery. Use `(collab delete)` for permanent removal.
- **Status encoding:** Status is the authoritative source; do not encode archived state in the filesystem path. The transcript file stays at its original `records/YYYY-MM-DD-<slug>.md` path after archival.
- **Active cleanup:** Clearing `activeCollabId` means leaving the registry pointer empty. Subsequent routes must refuse target inference until the moderator runs `(collab activate <record>)` or names a target explicitly.
- **Clear notice:** After archiving, the helper prints a `NEXT:` line, then an `EFFICIENCY:` line, then the collab id, then the trailing lifecycle notice. By default (no `--json`) that notice renders as the single line `NOTICE: Run /clear before starting another collab.`; pass `--json` to receive the structured `{"notice": "clear", "status": "archived", "message": "..."}` record instead — shape owned by [invariants.md](../../../commands/collab/reference/invariants.md) Note 3. Display the `NEXT:` line and the trailing notice to the caller. Route docs describe the output; they do not reimplement it.
- **No summary emission:** `archive` does not write, modify, or require a `### Summary —` block. Automatic close-summary generation belongs to `(collab run plan)`'s auto-close path; see [`run-plan/index.md`](../run-plan/index.md).

```route-arg
dispatch: (collab archive [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
