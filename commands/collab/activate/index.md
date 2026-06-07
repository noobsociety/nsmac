# /collab activate

Select the active collab in the registry so subsequent routes do not need an explicit target token.

## Trigger

**Slash:** `/collab activate`
**Signature:** `/collab activate <record>`
**Prose dispatch:** `(collab activate ...)` — prose routing hint; not a terminal command.
**Search phrases:** collab use, select active collab, switch active collaboration

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve `<record>` from the next positional token after `activate`. If missing, **ABORT**: `<record>` is required.
2. Read the resolved registry. If unreadable, **ABORT**: registry unreadable; name the path.
3. Resolve `<record>` against collab `slug`, `id`, or stable numeric position. If no entry matches, **ABORT**: registry target unavailable; name the token.
4. If the matched collab is archived, **ABORT**: registry target archived; name the token.
5. Write the matched collab id to `activeCollabId`.
6. Stop after selecting the active collab. Do not modify the transcript.

## Notes

- **Parameters:** `<record>` — required collab slug, id, or numeric `#N`.
- **Active selection model:** the resolved registry stores one top-level `activeCollabId` pointer. `/collab activate` is the only normal route that changes that pointer directly.

```route-arg
dispatch: (collab activate <record>)
param: name=<record>; required=required; placeholder=<record>; class=dynamic; rule=collab slug, id, or #N from the registry
```
