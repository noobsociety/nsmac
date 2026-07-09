# (collab restore)

Move the active phase back by one step, or restore the collab's registry content to a specific point in the revision ledger.

## Trigger

**Dispatch:** `(collab restore [--to <eventIndex>])` — routing-only command form; not a shell command.
**Search phrases:** collab prev, previous collaboration phase, rollback collab phase, restore collab event, collab restore revision

## Steps

**Phase restore** (no `--to` flag — moves the active-phase pointer back one step):

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: record is closed.
4. Resolve the current phase from registry `activePhase`. If missing or unknown, **ABORT**: active phase missing in metadata.
5. Resolve the previous phase from **Phase sequence** in **Notes**. If no previous phase exists, **ABORT**: no previous phase; sequence exhausted.
6. Update registry `activePhase` to the previous phase by calling `commands/collab/engine/registry.py advance <target> prev`; the helper also renders the transcript status table from the resulting registry state.
7. Confirm the helper recomputed `turnOrder` for the restored phase from participants and phase context. Moderator-included phases (`Audit`, `Discussion`) restore the moderator to the front of the order; moderator-excluded phases (`Conclusion`, `Action Plan`, `Handoff`, `Completion`) keep the moderator out; the reviewer is never placed in `turnOrder` directly.
8. Confirm the helper-updated Active phase cell in the transcript state table names the previous phase.
9. Stop after the helper updates registry and transcript. Never delete or rewrite existing contributions.

**Content restore** (`--to <eventIndex>` — restores the collab's registry entry to the state captured in the revision ledger at the given event):

1. Read invariants.md before executing; call the relevant helper fresh (Invariant #4). Resolve the target collab per **Registry targeting** in **Notes**.
2. Read the resolved registry. If unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: record is closed.
4. Parse `<eventIndex>` as a non-negative integer. If the value is missing, non-integer, a legacy-baseline placeholder, or not present in the collab's revision event directory (`<state-root>/revisions/<collabId>/`), **ABORT** (agent-honor-system): invalid event index; name the value and the revision event directory path. Use `(collab log)` to list valid event indexes.
5. Read the event file at the resolved path. Extract the `_legacyBefore` snapshot — the registry document as it was immediately before event `<eventIndex>` was recorded. This is pre-`<eventIndex>` state: `--to N` restores to what the registry contained just before event N happened.
6. Project only the target collab's entry from the `_legacyBefore` snapshot into the live registry. Do not wholesale-replace the registry document; all other collab entries remain as they are in the live registry.
7. Validate the projected entry against the normal registry schema. If validation fails, **ABORT** (agent-honor-system): restored entry fails validation; name the field.
8. Bump the write-guard `revision` counter and write a new revision event describing the restore (event type, source `eventIndex`, timestamp). The ledger is append-only; `--to` does not rewind or delete existing events.
9. Stop. Re-establish context with `commands/collab/engine/registry.py speak-state --resume <target> <role>` before issuing the next command.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `restore`; when absent, resolved per **Registry targeting** in **Notes**. `--to <eventIndex>` — optional flag; selects content-restore mode and names the revision ledger event to restore from. When absent, phase-restore mode is used.
- **Phase restore vs. content restore:** `(collab restore)` (no args) moves only the active-phase pointer — it does not change the registry content of any collab entry. `(collab restore --to <eventIndex>)` restores the collab's registry entry to the state captured in the revision ledger at event `<eventIndex>`. These are distinct operations; they do not compose or chain.
- **Pre-`<eventIndex>` semantics:** `--to N` restores to the registry state as it was immediately before event N was recorded. The event at index N stores the full registry document under `_legacyBefore` — the state that existed before the write that created event N. Consequently, `--to N` yields the same state that `(collab log)` shows as the entry immediately preceding event N. The event index shown by `(collab log)` is the same value to pass to `--to`; there is no offset.
- **Target-collab projection:** Content restore projects only the target collab's entry from the `_legacyBefore` snapshot. Other collab entries in the live registry are not affected. The restore never wholesale-replaces the registry document.
- **Seal-desync caution:** Content restore fully replaces the collab's registry entry with the `_legacyBefore` snapshot. Restoring to an event index that predates the seal write removes `verificationSeal` entirely. Restoring to an event index at or after the seal write carries `verificationSeal` forward exactly as it existed at that snapshot — including a `stale: false` reading even if the live collab had since gone stale for unrelated reasons — so its evidence (`executionEntries`, `touchedPaths`, `pathDigests`) may no longer match current `HEAD` content. After a content restore on a previously sealed collab, run `(collab diff)` to check for drift before sealing again.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Phase sequence:** `Audit` <- `Discussion` <- `Conclusion` <- `Action Plan` <- `Handoff` <- `Completion`.
- **Multi-phase rollback:** For rollbacks spanning more than one phase, use `(collab set active-phase <phase> --force)` directly rather than chaining sequential calls; this is the canonical batch rollback path.
- **Append-only rollback:** `(collab restore)` moves only the active-phase pointer. `(collab restore)` never removes headings, contributions, checklist items, or completion markers.
- **Recovery path:** If `commands/collab/engine/registry.py advance <target> prev` returns without the expected registry phase, restored turn order, or transcript status table change, **ABORT** (agent-honor-system): treat the missing mirror as a helper defect and do not hand-edit the status table except through a dedicated repair route.
- **Post-state resume signal:** After `(collab restore)` completes, re-establish collab context with `commands/collab/engine/registry.py speak-state --resume <target> <role>` before writing the next contribution.
- **Sync contract compliance:** `commands/collab/engine/registry.py advance prev` owns registry phase, turn-order restoration, and status-table rendering. No restore-path prose-rendered write is expected; any missing mirror is a helper defect under the sync contract in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md).

```route-arg
dispatch: (collab restore [--to <eventIndex>])
param: name=--to; required=optional; placeholder=<eventIndex>; class=type; rule=non-negative integer present in the collab's revision event directory; default=none
```
