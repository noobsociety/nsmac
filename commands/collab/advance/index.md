# (collab advance)

Open the next moderator-selected phase in a collaboration record and update the active phase metadata.

## Trigger

**Dispatch:** `(collab advance [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab next, next collaboration phase, advance collab record

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: record is closed.
4. Resolve the current phase from registry `activePhase`. If missing or unknown, **ABORT**: active phase missing in metadata.
5. Resolve the next phase from **Phase sequence** in **Notes**. If no next phase exists, **ABORT**: no next phase; sequence exhausted.
6. Call `commands/collab/engine/registry.py advance <target> next` to update registry `activePhase` to the next phase and render the transcript status table from the resulting registry state. When the managed header changes, the helper prints `HEADER-OVERWRITE:` first; the `NEXT:` guidance line follows, naming the next expected role or Completion execution state. Display this output before the phase and transition-notice output.
7. If the next phase is `Conclusion`, the helper removes the moderator role from registry `turnOrder` and syncs the Turn order cell before accepting Conclusion contributions.
8. Confirm the helper-updated Active phase cell in the transcript state table names the new phase.
9. Ensure the next phase heading exists. If missing, append it at the end of the transcript.
10. If the `advance` helper from Step 6 emits a structured transition notice after the `NEXT:` line and phase line, display it to the caller. The helper emits a `compact` notice when advancing Discussion → Conclusion, an `action-plan-shape` notice when advancing Conclusion → Action Plan, and a `subagent` notice when advancing Handoff → Completion. The same notices are emitted by `speak-lifecycle-live` when auto-advance triggers the same transitions.
11. Stop after updating registry, transcript, and any transition notice display. Do not write a participant contribution.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `advance`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Phase sequence:** `Audit` -> `Discussion` -> `Conclusion` -> `Action Plan` -> `Handoff` -> `Completion`.
- **Moderator gate:** The moderator decides when this route runs. The route never checks whether participants have said enough.
- **`NEXT:` guidance:** `advance` emits a `NEXT:` line before the phase line and any structured transition notice. In ordinary speak phases, it names the role that should run `(collab speak)` next. When entering `Completion`, it names the role that should run `(collab run plan)` next.
- **Transition notices:** `advance` emits a structured lifecycle notice on select transitions: `compact` when entering `Conclusion`, `action-plan-shape` when entering `Action Plan`, and `subagent` when entering `Completion` (shapes sourced from `transition_notice()` in `commands/collab/engine/phase_lifecycle.py`; the `compact` and `subagent` shapes are also cited in [invariants.md](../../../commands/collab/reference/invariants.md) Note 3). Output order is: any `HEADER-OVERWRITE:` line, the `NEXT:` line, then `EFFICIENCY:` for the `compact` and `subagent` cases only (per the **Advisory line ordering** section of [`helper-output.md`](../../../commands/collab/reference/helper-output.md); `action-plan-shape` adds no `EFFICIENCY:` line), then the phase-name line, then the notice itself. By default (no `--json`) the notice renders as a single `NOTICE: <message>` line rather than the raw structured record; pass `--json` to receive the structured record. The same notices are emitted when `speak-lifecycle-live` auto-advances through these transitions. Route docs describe this output; they do not duplicate the decision.
- **Recovery path:** If `commands/collab/engine/registry.py advance <target> next` returns without the expected registry phase or transcript status table change, **ABORT** (agent-honor-system): treat the missing mirror as a helper defect and do not hand-edit the status table except through a dedicated repair route.
- **Post-state resume signal:** After `(collab advance)` completes, re-establish collab context with `commands/collab/engine/registry.py speak-state --resume <target> <role>` before writing the next contribution.
- **Sync contract compliance:** Step 9's missing-heading repair is a prose-rendered transcript write. `commands/collab/engine/registry.py advance` owns registry phase, turn-order normalization, and status-table rendering. The heading repair is declared under the sync contract in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md).

```route-arg
dispatch: (collab advance [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
