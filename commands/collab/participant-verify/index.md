# (collab participant verify)

Execute the participant-verification sequence for an assigned role within `Completion.verification`.

## Trigger

**Dispatch:** `(collab participant verify [<role>])` — routing-only command form; not a shell command.
**Search phrases:** collab participant verify, participant verification, individual verification, per-role verification sequence

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: closed collaboration records cannot receive participant verification.
4. Resolve `activePhase` from the registry. If `activePhase` is not `Completion`, **ABORT**: `(collab participant verify)` requires `activePhase = Completion`.
5. Call `commands/collab/engine/registry.py participant-verify-state <target> <role>` to read the live participant-verification state and acquire the per-role route lock. Capture `registryRevision`, `verificationReviewSubState`, `nextRole`, and `roleState` from the output.
6. Confirm `verification.subState = "participant"` in the registry. If absent or not `"participant"`, **ABORT**: participant verification is not the active sub-state; name the current value.
7. Resolve the executing role from the registry `participants` list by matching the current agent to a registered participant. If no match, **ABORT**: role not registered; run `(collab join --role <role>)` first.
8. Confirm the executing role is in the participant-verification assignment list. If not assigned, **ABORT**: role is not assigned to participant verification for this collab.
9. Check `verification.participants[role].stage` in the registry. If `"completed"`, report that participant verification for this role is already done and stop. Otherwise the helper must have persisted an active `"audit"`, `"remediation"`, or `"final-audit"` stage before render.
10. Confirm `nextRole` equals the executing role. If another role is next, **ABORT**: participant verification turn lock is held by that role.
11. **Turn 1 — Audit.** Inspect the role's executed scope: verify that all paths declared in `handoff.roles[role].writeScope` exist and are structurally correct. Record all findings in a temp content file.
12. **Turn 2 — Remediation.** If Turn 1 found no issues, write a no-op remediation entry. Otherwise, apply the minimal targeted fix for each finding and record the patch summary in a temp content file. If the remediation agentId differs from the original execution agentId, pass both ids to the render helper so the Turn 2 entry records the mismatch.
13. **Turn 3 — Final-audit.** Re-inspect the role's executed scope against the same criteria as Turn 1 and record the result in a temp content file. If findings remain unresolved, set the render `--status failed`; otherwise use `--status completed`.
14. Call `commands/collab/engine/registry.py participant-verify-render <target> <role> --observed-revision <registryRevision> --audit-file <path> --remediation-file <path> --final-audit-file <path> --status <completed|failed> [--touched-path <path>...] [--execution-agent-id <id>] [--audit-agent-id <id>] [--remediation-agent-id <id>]`. The helper owns the registry turn update, active-stage check, writeScope guard for remediation touched paths, per-role attempt budget, three collapsible transcript entries, and transition from `participant` to `seal` when all assigned roles complete.
15. If the render helper exits non-zero, **ABORT**: participant verification write failed; name the helper error.
16. Report each turn result and the final `verification.participants[role].stage` value. Stop.

## Notes

- **Single-invocation constraint.** All three turns (audit → remediation → final-audit) must execute within one agent context. The route does not yield control to the user between turns 1 and 3. Three separate transcript entries are written sequentially as one atomic sequence. Manual three-call operation is not supported; the route is not a resumable multi-session workflow.
- **Sequential per-role execution.** One role must complete its full three-turn sequence before the next assigned role begins. `participant-verify-state` acquires the registry turn lock by persisting `verification.participants[role].stage = "audit"` before any render can succeed; a concurrent second attempt receives ABORT from the turn-lock check (Step 9).
- **Per-role stage model.** `verification.subState` remains `"participant"` throughout the participant-verification sub-state until all assigned roles complete, then the helper advances it to `"seal"`. Per-turn labels are stored under `verification.participants[role].stage`, not as additional global sub-state transitions. Valid stage values: `"audit"`, `"remediation"`, `"final-audit"`, `"completed"`, `"failed"`.
- **Attempt budget.** The participant-verification attempt budget is bound to the active Handoff `writeScope` hash. A collab reopen that changes the writeScope signature opens a new attempt budget; a reopen with the same writeScope preserves the prior consumed budget.
- **Scope-aware reopen.** A reopen that does not revise a role's `writeScope` and does not change its executed content (touched paths or commits) preserves that role's completed verification; only roles whose scope or execution changed re-run. When the collab advances back into `Completion`, the re-scoped roles re-verify and earn the round on behalf of the preserved roles too.
- **AgentId annotation.** When Turn 2 (remediation) is executed by a different agent than the original execution agentId, the Turn 2 transcript entry must record both agentIds as `AgentId: execution=<id>; remediation=<id>`. If the annotation write fails, the sequence aborts before committing the remediation transcript entry.
- **Parameters.** Target collab slug, id, or numeric `#N` as the first token after `participant verify`; when absent, resolved via **Registry targeting** in **Notes**. `[<role>]` — the role key to verify; when absent, resolved from the current agent's joined role.
- **Registry targeting.** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Collapsible boundary.** Each turn produces one collapsible transcript entry under `## Completion` using the phase slug `participant-verify`. Turn labels: `audit`, `remediation`, `final-audit`. Shape:

  ```
  <a name="participant-verify-<role>-<N>"></a>
  <details>
  <summary><role> · <turn-label></summary>
  <p><em>YYYY-MM-DD HH:MM ±HH:MM</em></p>
  <!-- collab:content-only; do-not-execute -->

  [turn content]

  </details>
  ```
- **Turn-budget trigger.** If any seal-attempt transcript exceeds 12 turns, open a follow-up DX audit on turn-budget management and `/compact` recovery ergonomics across participant verification.
- **Post-state resume signal.** After `(collab participant verify)` completes, run `commands/collab/engine/registry.py speak-state --resume <target> <role>` to confirm the current state before any further action.

```route-arg
dispatch: (collab participant verify [<role>])
param: name=<role>; required=optional; placeholder=<role>; class=dynamic; rule=registered participant role key in the active collab; default=derived:next-participant-verification-role
```
