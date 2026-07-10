# Agent model and harness

## Trigger

**Dispatch:** (reference only — not an invocable route)
**Search phrases:** collab agent model, collab harness model, role model matrix

## Steps

1. Read this document when selecting or auditing collab role model and harness recommendations.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The document defines curated join-time model and harness guidance, a generated effort projection, and fallback behavior. The document supplements [`agent-effort.md`](agent-effort.md) (effort levels) and [`agent-lifecycle.md`](agent-lifecycle.md) (lifecycle command timing). For the role schema and roster, see [`platform/standards/role-standard.md`](../../../platform/standards/role-standard.md); for agentId precedence and capture semantics, see [`join.md`](../join/index.md).

**Authoritative source:** The file is authoritative for join-time model and harness guidance. `agent-effort.json` is authoritative for effort matrix values; the table below is a generated projection checked by `commands/collab/engine/registry.py audit-effort-matrix`.

## Join-time model and harness

Join-model recommendations are advisory: the registry records `agentId` at join time as an honest-effort forensic capture, not an enforced constraint. To assign a different agent to a role, pick the intended agent when running `(collab join)`.

The table below captures recommended defaults for curated roles. Identifiers name a model family or tier, not a version. They rotate quarterly; a different model family re-evaluates each row on each rotation. When `dcc` is in use, it resolves version pinning for curated launch shortcuts; consult this table for all other harness selection. Registered roles absent from this table use the caller-selected agent and harness until a row is explicitly added.

| Role | Join model | Harness |
|------|------------|---------|
| mod | n/a (human) | Codex CLI (codex-spark) |
| tw | `sonnet` | Claude Code |
| pe | `sol` | Codex CLI |
| pa | `opus` | Claude Code |
| tl | `fable` | Claude Code |

**Moderator harness.** Moderator turns are human-authored. `codex-spark` with `/fast` applies [`moderator-polish.md`](moderator-polish.md) by default and `--verbatim` bypasses that transform. Spark runs on a separate pool from `codex`, is scoped to moderator speed and transcript hygiene only, and must not be used for implementation judgment, convergence review, or action-plan ownership. If Spark is unavailable, use the fastest low-cost Codex CLI helper that preserves the moderator boundary; `mini` is the current fallback example.

**Platform-engineer join-model variants.** Use the default join model (see table above) for standard collabs. Use the light-advisory variant when cap preservation matters. Use the implementation-only harness variant only when joining narrowly for execution in Completion. Do not use the moderator-speed model pool as the join model for a full platform-engineer collab.

**Reviewer fallback.** Use the lower-tier join model when the reviewer cap is exhausted or the collab is lightweight with no convergent-gate weight. The reviewer join model is cap-fragile under sustained use; Claude Max sustains roughly 2–3 reviewer-role collabs per rolling cap window.

## Dimension rationale

`dimensions` values (see `platform/standards/role-standard.md`'s "Dimensions semantics") were assigned per role on each model's demonstrated strength, argued in the `2026-07-02-concerns-taxonomy` collab:

| Role | Dimensions | Rationale |
|------|-----------|-----------|
| tw | `narrative` | `sonnet`'s prose fluency maps directly to docs/transcript legibility. |
| pe | `product`, `hygiene`, `security`, `reliability` | `sol`'s flagship capability, adversarial coding, and tool-driven reasoning fit delivery, repository cleanup, security review, failure analysis, and evidence-backed assurance. |
| pa | `structure`, `architecture` | `opus`'s multi-hop reasoning fits file/slice layout and control-flow/state-model review. |
| tl | `strategy`, `delivery` | `fable`'s long-horizon planning and delegation fit goal alignment, dependencies, and coordinated execution. |

This table records rationale only and is not machine-read; `dimensions[]` in each role file under `commands/collab/reference/roles/` is the enforced value.

## Per-speak-turn effort

> **generated; do not edit** — this table is a projection of `agent-effort.json`; edit the JSON source instead.

| Phase | mod | tw | pe | pa |
|-------|-----|----|----|----|
| Audit | low | medium | medium | xhigh |
| Discussion | low | medium | high | high *(optional tail)* |
| Conclusion | low | medium | medium | xhigh |
| Action Plan | low | medium | high | — *(optional xhigh if admitted)* |
| Handoff | low | high | xhigh | — *(optional xhigh if admitted)* |
| Completion | low | high | high | xhigh *(reviewer gate; execution sub-state)* |
| Completion.verification | low | high | high | xhigh *(reviewer seal; mandatory-declaration turn)* |
| Completion.verification.participant | low | xhigh | xhigh | — |

Values must match the phase-role matrix in `agent-effort.json`. When the two diverge, `agent-effort.json` is authoritative; update this projection to match.

Registered roles absent from the generated projection receive the open-roster effort fallback documented in [`agent-effort.md`](agent-effort.md).

**Platform-engineer effort.** The `sol` rotation preserves the role's explicit phase settings: `medium` for Audit and Conclusion; `high` for Discussion, Action Plan, Completion, and Completion.verification; and `xhigh` for Handoff and Completion.verification.participant. `Completion` is the execution phase for `(collab run plan)`. A model rotation alone does not justify changing these values; compare the same effort and one level lower on representative phase workloads before reducing them.

## Reviewer at `Completion.verification`

The reviewer's two ordered modes (seal, then assessment), the verdict object shape, and staleness re-entry are owned by [`verification.md`](verification.md). Both modes are part of the reviewer's `Completion.verification` turn (`xhigh`, mandatory-declaration). The reviewer writes verdict fields only (evaluation); all correction work at the restored phase belongs to participants.

## Caveats

**Declared bias.** The original join-model recommendations for tw, pe, and pa were authored in the collab that produced them by candidates for those roles: tw by `sonnet`, pe by `gpt`, pa by `opus`. The Conclusion accepted the self-recommendations and declared the bias explicitly. The current `pe` rotation to `sol`, its merged assurance remit, and the later technical-lead mapping were maintainer-selected rather than self-recommended. The `mod` Harness recommendation (`codex-spark`) was made by Codex-family agents in Discussion; declared per quarterly-rotation principle.

**Quarterly cross-review.** On each rotation, a different model family re-evaluates whether the recommended family or tier is still the right choice for each role — not which version. The authoring agent must not serve as the sole reviewer of its own row.
