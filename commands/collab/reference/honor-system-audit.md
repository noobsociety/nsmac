# Honor-system clause audit

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** honor-system audit, agent-honor-system clauses, collab coverage gaps

## Steps

1. Read this document when auditing agent-honor-system clause coverage.
2. For each clause below, verify whether the helper has since added runtime enforcement; if so, remove the `agent-honor-system` marker and move the entry to a "Promoted" subsection.
3. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

Every `agent-honor-system` clause marks an ABORT that relies on agent judgment rather than runtime enforcement. Use the clause inventory below to track which clauses remain unverifiable by the helper and which carry known drift risk.

**Maintainer check:** `git grep -rn 'agent-honor-system' commands/` regenerates the full clause inventory. Every result must appear in the table below or be added. Absence is a defect.

## Clause inventory

| # | Source | ABORT anchor | Clause summary | Helper enforcement | Drift risk |
|---|---|---|---|---|---|
| 1 | `commands/collab/index.md:15` | `collab-invalid-route` | Invalid or missing route token after `(collab)`; agent names the received token and emits the route roster. | None — dispatch is prose-resolved by the agent, not the helper. | Low: any invalid token silently falls through without a standardized error shape, making it hard to detect routing failures in logs. |
| 3 | `commands/collab/seal-verification/index.md:42` (Notes) | `seal-verification-registry-target` | Registry target unavailable for `(collab seal verification)`; agent names the registry field or token. | Partial — `seal-state` enforces target resolution (`registry target not found`, `registry activeCollabId is empty`). The honor-system marker covers the human-facing naming obligation, not the gate itself. | Low: helper enforcement is the primary gate; this clause only adds the human-readable name obligation. |
| 4 | `commands/collab/reference/helper-output.md:213` | `seal-verification-archive-protocol-violation` | `--cap-exit archive` used when participant verification passed cleanly (no findings); protocol violation with no helper abort. | None — `seal-render` accepts `--cap-exit archive` regardless of participant-verification outcome. The constraint is route-prose-enforced only. | Medium: violations trigger the rollback condition in `invariants.md` Invariant #10. Detection is active but reactive; the helper cannot prevent the violation. |

## Promoted

| # | Source | ABORT anchor | Clause summary | Helper enforcement | Promoted in |
|---|---|---|---|---|---|
| 2 | `commands/collab/seal-verification/index.md:36` | `seal-verification-uncommitted-paths` | Step 12: implementation path listed in `touchedPaths` is unstaged and uncommitted in git. | Full — `seal-render` checks each execution `touchedPath` against committed or staged git state and rejects working-tree-only paths or touched paths with unstaged changes with `SEAL-GIT-STATE: implementation not in git`. | pe item, collab `2026-05-25-multi-agent-framework-assessment-eliminate-risks` |
| 5 | `seal-verification-zero-round-no-record` | `seal-verification-zero-round-no-record` | Step 8: `verificationRounds` is zero; agent must abort before sealing. Round increment moved from `seal_render` to `participant_verify_render` at the all-participants-completed transition; `seal_render` now checks `verificationRounds > 0` as defense-in-depth only. | Full — `participant_verify_render` owns the increment; `seal_render` defends in depth; agent judgment no longer required for this abort path. | pe item, collab `2026-05-19-multi-agent-framework-assessment-part-4` |

## Non-convergence observation (PA addition 3)

PA's Audit finding #3 (convergence by participation) is absorbed here rather than in the Action Plan. The observation: when a participant never joins a collab phase, their absence is indistinguishable from silence — the protocol has no signal for deliberate non-participation versus missing contributor. The observation appears beside the honor-system clauses because the failure shape is identical: documentation assumes participation, but the helper does not enforce it.

No helper change is planned. If a future collab shows repeated silent non-participation from a registered role, re-open this item with evidence.

## Drift detection

The `show-policy.md` **Honor-system / helper drift** note names the inverse gap: a route may still carry an `agent-honor-system` marker after the helper has begun enforcing the same abort path. The P9 coverage gate (`platform/tooling/coverage-gate.sh`) detects missing helper tests but does not detect stale honor-system markers. Run the maintainer check above after any helper enforcement is added to a previously honor-system path, and update this table accordingly.
