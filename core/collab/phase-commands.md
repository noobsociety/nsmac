# Collab Phase Commands

Quick-reference table: the commands each role invokes in each collaboration phase, in invocation order.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab phase commands, phase command reference, what commands per collab phase

## Steps

1. Read this document when orienting to the command sequence for a given phase or role.
2. Do not mutate registry or transcript state from this documentation-only reference.
3. Consult the source citations table for the authoritative route playbook step behind each cell.

## Notes

**Setup (before Audit):** Every role runs `/collab join --role <role>` on entry, then `/collab show policy` before the first contribution (`join.md` step 10 — advisory output; `show-policy.md` step 1). The moderator also runs `/collab init <name>` to create the collab and auto-join as the moderator role (`init.md` step 3).

## Phase commands

| Phase | mod | tw | pe | pa |
|---|---|---|---|---|
| Audit | `/collab speak` | `/collab speak` | `/collab speak` | `/collab speak` |
| Discussion | `/collab speak` (optional); `/collab advance` | `/collab speak` | `/collab speak` | `/collab speak` (optional) |
| Conclusion | `/collab speak` (optional) | `/collab speak` | `/collab speak` | `/collab speak` |
| Action Plan | `/collab speak` (optional) | `/collab speak` | `/collab speak` | — |
| Handoff | `/collab speak` (optional) | `/collab speak` | `/collab speak` | — |
| Completion | — | `/collab run plan`; `/collab participant verify` when configured | `/collab run plan`; `/collab participant verify` when configured | `/collab seal verification` |

**Notes**

- **Moderator advance:** The moderator role must call `/collab advance` to exit Discussion (required — Discussion does not auto-advance; `speak.md` step 13, Discussion/Completion exemptions). All other phase transitions auto-advance via `speak-lifecycle-live` after the last required contributor speaks.
- **Moderator in Conclusion–Handoff:** The moderator role is removed from `turnOrder` when Conclusion is entered (`advance.md` step 7). Moderator contributions from Conclusion onward are optional and require human-authored text (`speak.md` step 9).
- **Reviewer:** speaks last in Audit and Conclusion per `last-in-convergent-phases` (`join.md` step 8). Optional in Discussion (`speak.md` step 8, optional-reviewer tail-slot in `allowedRoles`). Absent from Action Plan and Handoff (`join.md` step 8, reviewer excluded from non-convergent-phase `turnOrder`; `speak.md` step 8, reviewer absent from `allowedRoles`). Issues `/collab seal verification` after assigned execution and configured participant verification complete.
- **`Completion.verification` sub-phases:** Within `Completion.verification`, configured participants first execute `verification.participant` via `/collab participant verify` one role at a time, then the reviewer executes `verification.seal` via `/collab seal verification`, followed by `verification.assessment` (evaluates whether discussion goals were met; emits a `verdict`). Assessment also re-opens when the seal becomes stale or a cap-exit is recorded. See [`verification.md`](verification.md) for the verdict schema and trigger conditions.
- **Internal gate:** `/collab speak` calls `speak-state` before `speak-render` to validate turn eligibility and capture `registryRevision` for the stale-write guard (`speak.md` step 8). This gate applies to every speak-phase cell above.
- **`—`:** role has no assigned turn in this phase.

## Source citations

| Phase | mod | tw | pe | pa |
|---|---|---|---|---|
| Audit | `speak.md` steps 9, 12 | `speak.md` step 12 | `speak.md` step 12 | `speak.md` step 12; `join.md` step 8 (`last-in-convergent-phases` seeding places reviewer last) |
| Discussion | `advance.md` step 6; `speak.md` step 9 | `speak.md` step 13 (Discussion exempt from auto-advance; multiple contributions permitted) | `speak.md` step 13 (Discussion exempt from auto-advance; multiple contributions permitted) | `speak.md` step 8 (optional-reviewer tail-slot admitted via `allowedRoles` in `reviewerOptionalPhases`) |
| Conclusion | `advance.md` step 7 (mod removed from `turnOrder`); `speak.md` step 9 | `speak.md` step 12 | `speak.md` step 12 | `speak.md` step 12; `join.md` step 8 (reviewer last per `last-in-convergent-phases`) |
| Action Plan | `speak.md` steps 9, 10 | `speak.md` step 10 | `speak.md` step 10 | `join.md` step 8 (reviewer excluded from `turnOrder` in non-convergent phases); `speak.md` step 8 (pa absent from `allowedRoles`) |
| Handoff | `speak.md` steps 9, 12 | `speak.md` step 12 | `speak.md` step 12 | `join.md` step 8 (reviewer excluded from `turnOrder` in non-convergent phases); `speak.md` step 8 (pa absent from `allowedRoles`) |
| Completion | `run-plan.md` step 7 (no `**mod:**` Action Plan items collected; nothing to implement — report and stop) | `run-plan.md` steps 5 (Completion-only guard), 6 (role resolution), 7 (unchecked item collection), 13 (scoped validation), 14 (checkbox update), 15 (execution recording); `participant-verify.md` steps 5–14 when participant verification is configured | `run-plan.md` steps 5 (Completion-only guard), 6 (role resolution), 7 (unchecked item collection), 13 (scoped validation), 14 (checkbox update), 15 (execution recording); `participant-verify.md` steps 5–14 when participant verification is configured | `seal-verification.md` steps 5–14 |

---

For effort levels per phase and role, see [`agent-effort.md`](../../core/collab/agent-effort.md).
