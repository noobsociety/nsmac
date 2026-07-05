# (collab unset reviewer)

Clear scoped collab metadata fields that have explicit empty-state semantics.

## Trigger

**Dispatch:** `(collab unset reviewer)` — routing-only command form; not a shell command.
**Search phrases:** collab unset, clear collaboration metadata, unset reviewer

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Resolve `<field>` from the next positional token after `unset`. If missing, **ABORT**: `<field>` is required.
3. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
4. Validate field ownership against **Unsettable fields** in **Notes**. If `<field>` is not unsettable, **ABORT**: field not unsettable; name the field.
5. For `reviewer`, call `commands/collab/engine/registry.py unset <target> reviewer`. The helper removes `reviewerRole`, `reviewerMode`, and `reviewerOptionalPhases`, treats an already-absent reviewer as a no-op, and renders the transcript status and Reviewer sections from registry state.
6. Stop after updating registry and transcript metadata. Do not append a contribution.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `unset`; when absent, resolved per **Registry targeting** in **Notes**. `<field>` — required field name. The only supported field in this pass is `reviewer`.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Unsettable fields:** `reviewer` -> removes reviewer assignment metadata. It clears `reviewerRole`, `reviewerMode`, and `reviewerOptionalPhases`; already-absent reviewer metadata is a no-op.
- **Deferred field coverage (dated scope note, 2026-06-24):** every other collab metadata field remains intentionally deferred, not accidentally omitted. `title`, `description`, `status`, `activePhase`, `moderatorRole`, `transcriptPath`, `id`, `slug`, and `terminal` are required lifecycle or identity fields under the live validator. `turn-order` is deferred because clearing it would reactivate participant-list fallback semantics and can change reviewer exclusion behavior; use `(collab set turn-order ...)` instead. `reviewer-optional-phases` is deferred because its empty state depends on an active `reviewerRole`; clearing all reviewer metadata is already covered by `unset reviewer`. `work-repo` is deferred because execution and seal checks require a concrete repository binding or the documented fallback semantics. Lifecycle evidence fields such as `verification`, `execution`, `verificationSeal`, `verdict`, `exportedIssues`, and `reopenCoverage` are cleared only by their owning lifecycle helpers, not by generic unset.
- **Idempotency:** `unset reviewer` succeeds when no reviewer is currently set. The command still aborts on unreadable records, schema validation failure, transcript write failure, or closed and archived records.
- **Ownership boundary:** `(collab unset)` is the inverse surface for fields with defined empty states. `(collab unset)` is not a generic registry-key deletion command.
- **Post-state resume signal:** After `(collab unset)` completes, re-establish collab context with `commands/collab/engine/registry.py speak-state --resume <target> <role>` before issuing the next collab command.
