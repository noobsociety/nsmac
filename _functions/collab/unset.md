# /collab unset

Clear scoped collab metadata fields that have explicit empty-state semantics.

## Trigger

**Slash:** `/collab unset`
**Signature:** `/collab unset reviewer`
**Prose dispatch:** `(collab unset ...)` — prose routing hint; not a terminal command.
**Search phrases:** collab unset, clear collaboration metadata, unset reviewer

## Steps

1. Read [_invariants.md](_invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Resolve `<field>` from the next positional token after `unset`. If missing, **ABORT**: `<field>` is required.
3. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
4. Validate field ownership against **Unsettable fields** in **Notes**. If `<field>` is not unsettable, **ABORT**: field not unsettable; name the field.
5. For `reviewer`, call `tools/collab/registry.py unset <target> reviewer`. The helper removes `reviewerRole`, `reviewerMode`, and `reviewerOptionalPhases`, treats an already-absent reviewer as a no-op, and renders the transcript status and Reviewer sections from registry state.
6. Stop after updating registry and transcript metadata. Do not append a contribution.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `unset`; when absent, resolved per **Registry targeting** in **Notes**. `<field>` — required field name. The only supported field in this pass is `reviewer`.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Unsettable fields:** `reviewer` -> removes reviewer assignment metadata. Other fields are intentionally out of scope until their empty-state semantics and schema rules are explicitly defined.
- **Idempotency:** `unset reviewer` succeeds when no reviewer is currently set. It still aborts on unreadable records, schema validation failure, transcript write failure, or closed and archived records.
- **Ownership boundary:** `/collab unset` is the inverse surface for fields with defined empty states. It is not a generic registry-key deletion command.
- **Post-state resume signal:** After `/collab unset` completes, re-establish collab context with `tools/collab/registry.py speak-state --resume <target> <role>` before issuing the next collab command.
