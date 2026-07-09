# (collab status)

Show the current workflow state of a collaboration record — not the registry `status` field (which is the lifecycle value `open`, `closed`, or `archived`) but the full runtime picture: active phase, turn order, reviewer configuration, participant list, and counter values. Use `(collab list)` to filter collabs by their `status` field.

## Trigger

**Dispatch:** `(collab status [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab status, collab state, current phase, collaboration state

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Call `commands/collab/engine/registry.py status-view <target>`.
3. Display the helper output exactly. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `status`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Naming disambiguation:** This route's name (`status`) reuses the same word as the registry field `status` (`open` / `closed` / `archived`). The route shows workflow state; the field records lifecycle state. To filter by lifecycle state, use `(collab list --status <open|closed|archived>)`.
- **Output shape:** Structured key-value display. Includes: `id`, `slug`, `title`, `status` (lifecycle), `activePhase`, `completionSubState` (when in Completion for a reviewer-backed collab), `turnOrder`, `reviewerRole`, `reviewerMode` (when a reviewer is set), `revision` (write-guard counter), `uncheckedAssignedItemsByRole` (when in Completion for a reviewer-backed collab), and participant rows. Example:

  ```
  id:           a13dba4ca8714205b217dca31da96eee
  slug:         collab-state-observability
  title:        Collab State Observability
  status:       open
  activePhase:  Completion.execution
  completionSubState: execution
  turnOrder:    tw, pe
  reviewerRole: pa
  reviewerMode: last-in-convergent-phases
  revision:     2423
  uncheckedAssignedItemsByRole: {"pe": 1, "tw": 0}
  participants: tw (claude-sonnet-4-6), pe (codex), pa (opus)
  ```

- **Counter displayed:** The `revision` field is the write-guard counter sourced from the `revision` field in `registry.json`. See [schema-evolution.md](../../../commands/collab/reference/schema-evolution.md) for the counter lifecycle. The helper-output label for this value may differ from the stored field name.
- **Read-only:** The route does not mutate registry state or transcript text.

```route-arg
dispatch: (collab status [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
