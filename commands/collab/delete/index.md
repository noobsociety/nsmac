# (collab delete)

Permanently remove a collab record from the registry and disk. The operation is destructive and requires explicit confirmation.

## Trigger

**Dispatch:** `(collab delete [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab delete, hard delete collab, permanently remove collaboration record

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. Require explicit confirmation before proceeding: display the collab slug, id, and transcript path. Gate the deletion per `platform/standards/command-argument.md`:

   ```route-gate
   gate-class: destructive
   proceed: delete <slug>
   abort: cancel
   operand-format: collab registry id
   invalid-input: re-prompt
   re-prompt-template: Type "delete <slug>" (replacing <slug> with the collab id) to confirm permanent deletion, or "cancel" to abort.
   ```

   If the user does not type the exact proceed token, stop without any change.
4. Remove the collab entry from the registry entirely.
5. Clear `activeCollabId` when it points at the deleted collab.
6. Delete the transcript file and its contribution store file from disk.
7. Stop after registry removal, transcript deletion, and contribution store deletion.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `delete`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Destructive by default:** `delete` is always a hard delete — it removes the registry entry, the transcript file, and the transcript's contribution store file. For non-destructive deactivation, use `(collab archive)` instead.
- **Confirmation required:** Always show the target details before presenting the gate. Never skip the gate prompt. Gate contract: `platform/standards/command-argument.md`.

```route-arg
dispatch: (collab delete [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
