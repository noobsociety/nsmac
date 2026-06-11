# /collab aggregate

Render the moderator project transcript (`records/<slug>.md`) as a deterministic, project-labeled projection derived from canonical registry state and the contribution store. The aggregator writes `records/<slug>.md` only; it never writes `records/<slug>-raw.md`. The raw transcript is written by lifecycle operations (speak, advance, reopen) and is never projection input.

## Trigger

**Slash:** `/collab aggregate`
**Signature:** `/collab aggregate`
**Prose dispatch:** `(collab aggregate)` — prose routing hint; not a terminal command.
**Search phrases:** collab aggregate, moderator project transcript, render projection, aggregate transcript

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
<!-- abort: aggregate-record-unreadable -->
2. Read the resolved registry and resolved contribution store. If either is unreadable, **ABORT**: `ABORT: record unreadable. Check the registry and contribution-store paths.`
<!-- abort: aggregate-project-label-missing -->
3. Resolve `registry.project.label`. If absent, **ABORT**: `ABORT: project label missing. Add project.label to the registry before aggregating.`
4. Derive the projection from registry state and the contribution store only. Do not read or parse `records/<slug>-raw.md` bytes as input; see **Projection input contract** in **Notes**.
5. For each contribution block in the contribution store, validate: source anchor resolves, stance state is either an author-declared closed-vocabulary token or the renderer-owned `missing-stance` sentinel, and excerpt source traces to a raw anchor or a registry field. If any validation fails, apply the **Abort template** from **Notes**.
6. Render the moderator project transcript: each block labeled from `registry.project.label`, each stance row carrying source anchor, source role, stance state, and bounded display excerpt (see **Excerpt cleanliness** in **Notes**). Include a raw anchor link on each row as the escape-hatch to the full contribution body.
7. Write the output to `records/<slug>.md`. Append a staleness footer noting the registry revision and content digest. Do not write to `records/<slug>-raw.md`.
8. Do not advance lifecycle state. Aggregate is a view-refresh operation; it does not constitute a turn, satisfy a phase gate, or drive convergence.
9. Report the output path, registry revision rendered, and content digest.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `aggregate`; when absent, resolved per **Registry targeting**.
<!-- abort: aggregate-registry-target -->
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: `ABORT: registry target unavailable. Name the registry field or token.`
- **Projection input contract:** Projection input is registry state plus the contribution store. `records/<slug>-raw.md` is written by lifecycle operations (speak, advance, reopen), not by the aggregate renderer; it is never parsed as projection input. A three-tier chain — registry → raw → projection — introduces parse-round-trip drift whose fidelity depends on the markdown parser rather than canonical state. Both raw and projection are reproducible from registry state independently at any revision (Invariant #2, Invariant #4). The canonical input description is "registry state plus the contribution store"; do not use "registry plus raw" or any phrasing that makes raw a projection input.
<!-- abort: aggregate-abort-template-note -->
- **Abort template:** All abort messages follow `ABORT: <condition>. <recovery hint>.` — consistent with the `speak-render` abort surface. Named abort messages: missing or invalid stance token: `ABORT: stance token missing or invalid for <anchor>. Add a valid stance declaration to the source contribution before aggregating.`; unresolvable raw anchor: `ABORT: raw anchor <anchor> unresolvable. Verify the source contribution exists in the contribution store.`; digest mismatch: `ABORT: projection digest mismatch at revision <N>. Rerender from current registry state.`
- **Determinism contract:** Same registry revision and contribution store → same output bytes. The renderer must not call generative functions, paraphrase, or introduce prose not traceable to a raw source anchor or a registry field. "Polished" means deterministically structured — phase grouping, stable labels, source anchors, status callouts, staleness footer — not interpretively summarized. A projection can be DX-excellent while remaining fully mechanically derived; every word not copied verbatim from a raw moderator contribution must trace to a registry field.
- **Stance vocabulary:** Author-declared stance tokens are the closed set `converges`, `dissents`, `qualifies`. The renderer-owned absence sentinel is `missing-stance`. No other stance states are valid. Extensions require a change to this doc. The renderer validates stance state at render time; it never infers stance from free prose.
- **Author-declared stance:** `/collab speak` captures a leading `STANCE: converges`, `STANCE: dissents`, or `STANCE: qualifies` marker into the contribution store and hides it from rendered raw transcript prose. If the marker is absent, the store records `missing-stance`, and aggregate renders that visible missing-state instead of defaulting to `qualifies` or guessing from free prose. Historical records that carry a silent default are recomputed from stored content and surface as `missing-stance` when no source marker exists.
- **Excerpt cleanliness:** The displayed excerpt is substantive body only. Before rendering, strip from each raw contribution block: (a) content-only scaffolding — `<p><em>…</em></p>` timestamp lines and `<!-- collab:content-only; do-not-execute -->` comment lines; (b) hidden metadata — `STANCE: ...`, `EFFORT OVERRIDE:` lines, and §9.1 directive-gap markers (`**Directive:** "…"` and `**Action Plan: …**` opening lines). Stripped content never appears in the rendered projection table and does not count against the excerpt word limit.
- **Projection label:** The projection block label derives from `registry.project.label`. Using an informal alias (`Ag:`, `aggregator:`, or any role key) is rejected; the label must trace to a named registry field, making block attribution deterministic and auditable.
- **Non-lifecycle:** Aggregate does not advance convergence, phases, or any lifecycle state. An aggregate call is not a turn and must not be treated as phase advancement. Phase transitions are driven by the `speak-lifecycle` helper; aggregate is a view refresh only.
- **Moderator project transcript:** The canonical name for `records/<slug>.md` is **moderator project transcript**. Do not use "projection plane," "moderator-facing path," or bare "project transcript" in route docs, code comments, or error messages. `records/<slug>-raw.md` is the **raw transcript**. Both terms are enumerated in the glossary.
- **Staleness footer:** The moderator project transcript includes a footer with the registry revision and content digest from which it was rendered. The footer is mechanically generated; never hand-edit it.
- **Read/write ownership:** `records/<slug>.md` (moderator project transcript) is written exclusively by the aggregator and read by the moderator only. `records/<slug>-raw.md` (raw transcript) is written by lifecycle operations (speak, advance, reopen) and read by all participants except the moderator. The aggregator must never write `records/<slug>-raw.md`; lifecycle operations must never write `records/<slug>.md` directly. This separation keeps the moderator's view deterministic and prevents raw contribution noise from appearing in the projection without aggregation. Step 7 enforces the aggregator side of this invariant.
- **See also:** [`invariants.md`](../reference/invariants.md) — Invariants #2, #4, #17, #19; [`open/index.md`](../open/index.md) — moderator transcript view and `--raw` advisory; [`handoff-shape.md`](../reference/handoff-shape.md) — writeScope and validationCommands contract.
