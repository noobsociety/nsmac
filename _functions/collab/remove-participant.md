# /collab remove participant

Remove one participant from the registry roster and transcript metadata when the moderator needs to change the collaboration roster.

## Trigger

**Slash:** `/collab remove participant`
**Signature:** `/collab remove participant <role>`
**Prose dispatch:** `(collab remove participant ...)` — prose routing hint; not a terminal command.
**Search phrases:** collab kick, remove collab participant, drop collaboration role

## Steps

1. Read [_invariants.md](_invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Resolve `<role>` from the next positional token after `remove participant`. If missing, **ABORT**: `<role>` is required.
3. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
4. If `<role>` is not listed in registry `participants`, report that the role is already absent and stop.
5. If `<role>` equals registry `moderatorRole`, **ABORT**: moderator cannot be removed by `/collab remove participant`; replace the moderator first.
6. If `<role>` equals registry `reviewerRole`, **ABORT**: reviewer cannot be removed while assigned; run `/collab set reviewer --clear` first to remove the reviewer assignment, then re-run `/collab remove participant`.
7. Remove `<role>` from registry `participants` and registry `turnOrder`.
8. Remove the role's participant row from the participants table. If no participants remain, restore the placeholder row `| — | — | — | — | — |`. Sync the Turn order cell in the transcript state table from registry `turnOrder`; write `—` when registry `turnOrder` is empty, otherwise write the space-separated keys.
9. Stop after updating registry and transcript. Do not remove prior phase contributions.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `remove participant`; when absent, resolved per **Registry targeting** in **Notes**. `<role>` — required participant key to remove.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Ownership boundary:** `participants` are owned by `join` and `kick`. `/collab set` must not replace the roster during normal operation.

```route-arg
dispatch: (collab remove participant <role>)
param: name=<role>; required=required; placeholder=<role>; class=dynamic; source=tools/collab/registry.py roles
```
