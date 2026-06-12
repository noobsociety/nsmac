# (collab archive)

Soft-delete a collab by marking it archived so it is preserved on disk but excluded from active routing.

## Trigger

**Dispatch:** `(collab archive [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab archive, archive collab, soft-delete collab record

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is already `archived`, report that the record is already archived and stop.
4. Set registry status to `archived` and `archived` to `true`. The helper emits a structural `### Summary —` block under `## Completion`, creating the section if absent.
5. If the archiving collab id matches `activeCollabId`, clear `activeCollabId`. Do not change the active pointer when it selects a different collab.
6. Display the clear notice emitted by the helper after the status change completes.
7. Stop after registry cleanup, summary emission, and the clear notice display. Do not move or delete the transcript file.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `archive`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Soft delete:** `archive` marks the record inactive without touching the transcript file. The record remains on disk for auditability and recovery. Use `(collab delete)` for permanent removal.
- **Status encoding:** Status is the authoritative source; do not encode archived state in the filesystem path. The transcript file stays at its original `records/YYYY-MM-DD-<slug>.md` path after archival.
- **Active cleanup:** Clearing `activeCollabId` means leaving the registry pointer empty. Subsequent routes must refuse target inference until the moderator runs `(collab activate) <record>` or names a target explicitly.
- **Clear notice:** The helper emits `{"message": "Run /clear before starting another collab.", "notice": "clear", "status": "archived"}` after archiving. Display this to the caller. Route docs describe the output; they do not reimplement it. See [invariants.md](../../../commands/collab/reference/invariants.md).
- **Summary-emission invariant:** A `### Summary —` block is written to `## Completion` at archive; no follow-up step is required.

```route-arg
dispatch: (collab archive [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
