# /collab delete

Permanently remove a collab record from the registry and disk. This operation is destructive and requires explicit confirmation.

## Trigger

**Slash:** `/collab delete`
**Signature:** `/collab delete [<target>]`
**Prose dispatch:** `(collab delete ...)` — for non-Cursor agents; not terminal-executable in Cursor.
**Search phrases:** collab delete, hard delete collab, permanently remove collaboration record

## Steps

1. Read [_invariants.md](_invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. Require explicit confirmation before proceeding: display the collab slug, id, and transcript path. Gate the deletion per `cursor/_core/command-argument.md`:

   ```cursor-gate
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
6. Delete the transcript file from disk.
7. Stop after registry removal and transcript deletion.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `delete`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Destructive by default:** `delete` is always a hard delete — it removes both the registry entry and the transcript file. For non-destructive deactivation, use `/collab archive` instead.
- **Confirmation required:** Always show the target details before presenting the gate. Never skip the gate prompt. Gate contract: `cursor/_core/command-argument.md`.

```cursor-arg
dispatch: (collab delete [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
