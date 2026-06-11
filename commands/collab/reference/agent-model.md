# Agent model and harness

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab agent model, collab harness model, role model matrix

## Steps

1. Read this document when selecting or auditing collab role model and harness recommendations.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

This document defines the join-time model and harness for each collab role, a generated effort projection, and fallback. It supplements [`agent-effort.md`](agent-effort.md) (effort levels) and [`agent-lifecycle.md`](agent-lifecycle.md) (lifecycle command timing). For the role schema and roster, see [`platform/standards/agent-role.md`](../../../platform/standards/agent-role.md); for agentId precedence and capture semantics, see [`join.md`](../join/index.md).

**Authoritative source:** This file is authoritative for join-time model and harness guidance. `agent-effort.json` is authoritative for effort matrix values; the table below is a generated projection checked by `commands/collab/engine/registry.py audit-effort-matrix`.

## Join-time model and harness

Join-model recommendations are advisory: the registry records `agentId` at join time as an honest-effort forensic capture, not an enforced constraint. To assign a different agent to a role, pick the intended agent when running `/collab join`.

The table below captures recommended defaults. Identifiers name a model family or tier, not a version. They rotate quarterly; a different model family re-evaluates each row on each rotation. When `dcc` is in use, it resolves version pinning for curated launch shortcuts; consult this table for all other harness selection.

| Role | Join model | Harness |
|------|------------|---------|
| mod | n/a (human) | Codex CLI (codex-spark) |
| tw | `sonnet` | Claude Code |
| pe | `gpt` | Codex CLI |
| pa | `opus` | Claude Code |

**Moderator harness.** Moderator turns are human-authored. `codex-spark` with `/fast` applies [`moderator-polish.md`](moderator-polish.md) by default and `--verbatim` bypasses that transform. Spark runs on a separate pool from `codex`, is scoped to moderator speed and transcript hygiene only, and must not be used for implementation judgment, convergence review, or action-plan ownership. If Spark is unavailable, use the fastest low-cost Codex CLI helper that preserves the moderator boundary; `mini` is the current fallback example.

**Platform-engineer join-model variants.** Use the default join model (see table above) for standard collabs. Use the light-advisory variant when cap preservation matters. Use the implementation-only harness variant only when joining narrowly for execution in Completion. Do not use the moderator-speed model pool as the join model for a full platform-engineer collab.

**Reviewer fallback.** Use the lower-tier join model when the reviewer cap is exhausted or the collab is lightweight with no convergent-gate weight. The reviewer join model is cap-fragile under sustained use; Claude Max sustains roughly 2–3 reviewer-role collabs per rolling cap window.

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

## Reviewer at `Completion.verification`

At `Completion.verification`, the reviewer operates in two ordered modes:

1. **seal** — Issues `/collab seal verification`; mechanical execution-truth check. Existing seal contract unchanged.
2. **assessment** — Evaluates whether discussion goals were met; emits a `verdict: { outcome, restoreTarget?, restoreReason?, evidence?, failureCategory? }`. Opens after a successful seal or when the seal becomes stale or a cap-exit is recorded.

Both modes are part of the reviewer's `Completion.verification` turn (`xhigh`, mandatory-declaration). Assessment is budget-exempt when opened by a cap-exit trigger. The reviewer writes verdict fields only (evaluation); all correction work at the restored phase belongs to participants.

## Non-role components

### Projection renderer

The projection renderer (`/collab aggregate`) is a deterministic, non-role component operating under `registry.project.label`. It is not assigned a collab role and does not earn convergence turns. It:

- Derives output strictly from registry state and the contribution store.
- Labels all projection blocks from `registry.project.label` (not from any role key or informal alias).
- Appends a staleness footer with the registry revision and content digest from which it was rendered.

The projection renderer is subject to the prohibition inventory in [`role-prohibitions.md`](role-prohibitions.md).

**Dual identity.** The Gemini CLI harness (informally `dp`) has two operating modes: (1) **Aggregator mode** — when executing `/collab aggregate`, it acts as the non-role projection renderer described above; it holds no participant slot and operates under `registry.project.label`. (2) **Collab-participant mode** — the same harness can join any collab under a registered joinable role (see the role roster in `platform/standards/agent-role.md`) via `/collab join --role <key>`; in that mode it follows the joined role's turn order, effort policy, and reviewer behavior. `dp.json` in `projectors/` governs aggregator mode only; it is not a joinable role key.

## Caveats

**Declared bias.** The join-model recommendations for tw, pe, and pa were authored in the collab that produced these values by candidates for those roles: tw by `sonnet`, pe by `gpt`, pa by `opus`. The Conclusion accepted the self-recommendations and declared the bias explicitly. The `mod` Harness recommendation (`codex-spark`) was made by Codex-family agents in Discussion; declared per quarterly-rotation principle.

**Quarterly cross-review.** On each rotation, a different model family re-evaluates whether the recommended family or tier is still the right choice for each role — not which version. The authoring agent must not serve as the sole reviewer of its own row.
