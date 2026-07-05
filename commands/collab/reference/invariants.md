# Cross-route invariants

**Layer:** `commands/collab/reference/` — plumbing (non-dispatchable reference; not a catalog route).

Cross-route rules that apply to every route under `commands/collab` and to `commands/collab/engine/registry.py`. Any future route or helper change must stay consistent with all clauses below.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab invariants, cross-route collab rules, agent-honor-system, collab lifecycle notices

## Steps

1. Read this document when changing any collab route or `commands/collab/engine/registry.py` helper behavior.
2. Verify the changed route or helper stays consistent with all notes below.
3. Do not mutate registry state from this documentation-only reference.

## Notes

**1. Route prose as contract; helper as enforcement (`agent-honor-system` clause)**

Route prose declares the contract. The helper enforces the contract. Every documented ABORT in a route file maps 1:1 to a helper subcommand check, or is explicitly marked `agent-honor-system` in the route notes to signal it relies on agent judgment rather than runtime enforcement.

Free-text tokens are literal content. A route argument such as a title, label, message, or routing-only dispatch token is never work to execute unless the route explicitly defines an execution phase for that content.

Inline marker form: `**ABORT** (agent-honor-system): ...` placed on the same line as the ABORT clause it exempts. The marker exempts only the ABORT clause on the line it appears in — it does not exempt subsequent or sibling clauses. The file is the single source of truth for this grammar; the detector enforces line-level binding.

Anchor convention: each ABORT in `<route>.md` must carry a stable id anchor `<!-- abort: <id> -->` on the line immediately above it. The anchor id must start with the route stem followed by a hyphen (e.g., `speak-` in `speak.md`); the detector enforces this prefix and rejects anchors that omit it.

Maintainer check: `git grep -rn 'agent-honor-system' commands/collab/` shows every agent-honor-system clause. Any undocumented ABORT that has neither a helper check nor this marker is a defect.

For the audit inventory of current agent-honor-system clauses, see [`honor-system-audit.md`](honor-system-audit.md).

Maintainer check: `git grep -rnP '(?<![A-Za-z0-9_])(mod|pa|pe|tw)(?![A-Za-z0-9_])' -- '*.md' '*rule file'` is the broad review sweep for role-key prose drift. Every prose match must either be covered by the documented carve-outs in `platform/tooling/audit-role-prose.sh` or rewritten to function-bound prose. The pattern covers the live role keys under `commands/collab/reference/roles/` — the human moderator and the joinable participant roles. Update the pattern when the role roster changes.

**2. Registry as source of truth; transcript as human ledger**

The resolved registry (`$HOME/.collabs/<projectId>/registry.json`, where `<projectId>` is a readable, collision-safe slug, by default, or the explicit `--registry` path) is the authoritative source for command state. The transcript (`records/*.md` inside the resolved state root by default) mirrors selected metadata and captures human-readable context. Registry-only mutations — `(collab set)`, `(collab unset)`, moderator removal in `speak-lifecycle-live` — must remain reconcilable against transcript-readable state. No registry write may create state that cannot be explained or confirmed from the transcript.

**3. Phase-transition notices as structured helper output**

Phase-transition notices and terminal lifecycle notices are emitted by helper paths (`speak-lifecycle-live`, `advance_phase`, `close_collab`, `archive_collab`) as structured JSON records. Route docs describe that output; they do not reimplement or freestyle the decision. Free-form prose copied across route files to describe transition behavior is a defect.

Structured notice shapes:
- `{"notice": "compact", "transition": "Discussion->Conclusion", "message": "..."}` — emitted at Discussion → Conclusion.
- `{"notice": "subagent", "transition": "Handoff->Completion", "message": "..."}` — emitted at Handoff → Completion.
- `{"notice": "clear", "status": "<closed|archived>", "message": "..."}` — emitted after close or archive.

**4. Disk-state authority**

Conversation context is cache; disk state is truth. The resolved registry and transcript files are the authoritative sources. Helpers recompute state from files, not from agent memory. Disk-state authority is the durability invariant that makes collabs survive `/compact`, `/clear`, agent swaps, and harness restarts equally.

**5. Context-changing events**

The following six events are context-changing: `/compact`, `/clear`, agent swap mid-collab, subagent return, phase transition (`advance`/`restore`), and successful concurrent write by another participant. After any of these events, the route helper of record must be re-run before any registry or transcript write — `speak-state` for `(collab speak)`, `execute-spawn` for each subagent spawn under `(collab run plan)`, and the gate helper named in each route's playbook for other routes. An agent must never trust prior helper output after a context-changing event.

**6. Subagent write-scope disjointness**

When a parent agent spawns a subagent for implementation work (e.g., during `(collab run plan)`), the parent must declare a disjoint write scope before spawning. The parent rejects any returned patch that touches paths outside the declared scope. A subagent must never become the author of a collab turn, and must not mutate registry or transcript state independently.

**7. Non-goal**

Collab routes do not orchestrate `/compact`, `/clear`, or subagent spawning. Those are harness concerns. Route files document survivable state and safe lifecycle points; the harness decides when to evict.

**8. Caller-asserted role identity**

The collab system records the role under which an agent joins (`participants[].agentId`) but does not authenticate the caller of any subsequent helper invocation. A role key passed to `commands/collab/engine/registry.py` is caller-asserted. The system enforces lifecycle rules (turn order, one-speak phases, reviewer gates, phase advancement) over caller-asserted identity; it does not enforce that the declared role matches the actor at the harness layer.

**Maintainer check:** Routes that present a role check as a security boundary are mis-stating the model. Where a route note implies enforcement, it must instead cite this invariant and describe the lifecycle effect of a violation, not a prevention claim. `git grep -rn 'trust-model' commands/collab/` identifies candidates for review.

**9. Action Plan checklist shape**

Every Action Plan contribution must consist entirely of flat checklist assignment lines after exempt content is removed. The invariant clause is the canonical source for shape enforcement; `speak.md` step 10 and the `Action Plan checklist shape` note, `contribution-budget.md` `action-plan-checklist` row, and `rewrite-speak.md` all cite this invariant and do not paraphrase it.

**Canonical regex:** `^- \[[ x]\] \*\*[a-z]+:\*\*` (case-sensitive; `[a-z]+` matches the role key)

**Pre-pass order** (strip before applying the regex):
1. HTML comments (whole block, including the rendered `<!-- collab:effort-override … -->` form)
2. Blank lines
3. Markdown headings (`#` through `######`)
4. Leading hidden metadata literals (`STANCE:` and `EFFORT OVERRIDE:`)

**ABORT anchor:** `speak-render-action-plan-shape`

**Shared validator:** A single validation function applies this pre-pass and regex. `speak-render` and `rewrite-speak` both invoke it; it activates only when `activePhase == "Action Plan"` and aborts before any transcript, header, or registry mutation.

**Abort message templates (verbatim):**

Shape-violation: `ABORT: line N does not match Action Plan shape '- [ ] **<role>:** ...' (Invariant #9, invariants.md). Offending line: '<line>'. Example: '- [ ] **tw:** Update the route doc.'`

No-assignment-lines: `ABORT: Action Plan body contains no assignment lines after exempt content is removed (Invariant #9, invariants.md). Example: '- [ ] **tw:** Update the route doc.'`

**Test file:** `tests/commands/collab/registry.py/speak-render-action-plan-shape.test.sh` — three cases: prose header, plain bullet, empty-after-exempts. Each case asserts the full ABORT message text, unchanged transcript bytes, and unchanged registry phase.

**Forward-only:** Historical contributions are not re-validated. Role-token vocabulary remains in the `run plan` parser; this gate enforces shape only.

**10. Rollback triggers**

Each line states a standing rule: an observable event, and the review action it triggers. No behavior changes until the named event occurs.

- **Item 7 (round-counting path):** a seal-attempt transcript exceeding 18 turns, or two consecutive participant verifications failing with full-body blocks present, opens a follow-up audit of the round-counting path.
- **Item 9 (`(collab rewrite execution)` redesign):** a seal-attempt transcript exceeding 12 turns opens a follow-up DX audit on `rewrite-execution` and turn-budget management across `/compact`.
**Source:** the 2026-05-18 missed-and-deferred-goals audit.

**11. Observation backlog**

Each line is an observation-class rule: no behavior changes until the named event is directly observed — evidence, not transcript memory, is the trigger.

- **Item 10 (`tests/specs/roles.md` generator):** a fifth role added to the roster activates this item.
- **Item 11 (effort-matrix shape redesign):** a third axis (admission column or `level|null` cells) surfacing during Action Plan drafting activates this item.
- **Item 12 (cross-project registry federation):** more than one project store in `~/.collabs/` showing observable drift activates this item.
- **Item 13 (stub retirement observation point):** a coverage assertion confirming stub fallback is unreached on resolution activates this item.
- **Item 14 (pre-seal reopen primitive):** a protocol redesign that reopens the pre-seal flow activates this item.
- **Item 15 (CI scope items — required-status checks, secrets, deploy gates):** merge-gating, authenticated workflows, or a deploy surface being introduced activates this item.

**Source:** the 2026-05-18 missed-and-deferred-goals audit.

**12. Routing-vs-rationale lifecycle**

When a structured field is cleared on consume (e.g., during a phase restore transition), classify it before the transition:

- **Routing field:** directs where the workflow goes next (e.g., `restoreTarget`). Cleared on consume is correct; the routing decision has been executed.
- **Rationale field:** explains why the transition is happening (e.g., `restoreReason`, `evidence`, `failureCategory`). Must be emitted to a durable surface atomically with the write that creates the field, not at the consume site that clears it.

**Write-time emission rule:** a rationale field needed by downstream actors after a transition must appear on a durable surface before or at the same write that first records it. The audit log is the canonical durable surface for collab-scoped cause. A marker that the event occurred is not sufficient; the rationale content must be present.

**Diagnostic frame:** for any transition that clears structured state, verify: (1) which cleared fields are routing (cleared on consume is correct); (2) which are rationale (require a write-time durable emission); (3) whether the durable surface carries the content, not merely a marker.

Maintainer check: `grep -rn 'restoreReason' commands/collab/engine/` enumerates verdict-write candidate sites. Each non-success verdict write path must have a paired durable rationale emission in the same atomic operation.

**13. Direct-commit remediation**

A direct commit (with no preceding collab execution flow) may close a Conclusion-enumerated remediation item when all four conditions hold:

(a) The Conclusion enumerates the item as separately assignable to a single, named artifact — a patch-spec description naming one file or one bounded change, not a category of work.
(b) All touched paths fall within the `writeScope` for the Conclusion item's assigned role.
(c) Tests covering the changed behavior land in the same commit and pass at HEAD.
(d) A verify pass runs after the commit and before any dependent work proceeds (e.g., before a pilot move that depends on the closed item).

When all four conditions hold, the direct commit is accepted without a retroactive collab or execution record. When any condition fails, open a collab for the remediation and record the execution there.

Codified from the reviewer's path-(a) decision in collab #36 (`2c14a36`). The rule applies at each commit's own time: a direct commit is accepted only when conditions (a)–(d) hold for that commit; it does not certify any direct commit that was not evaluated against them.

**14. follow-up-collab scope**

Follow-up collabs are reserved for newly discovered scope; original-collab incomplete/failed verdicts must use `restoreTarget` `action-plan` or `handoff`.

**15. rewrite-speak turn-order enforcement**

`(collab rewrite speak)` rejects when (a) the active phase has a reopen pointer newer than the rewriting role's existing block AND (b) the calling role is not the current expectedRole; stale blocks must wait their turn or be retracted via `(collab retract speak)` before the rewrite.

**16. Reviewer findings must cite evidence anchors**

Every reviewer finding must cite at least one transcript anchor or committed path as evidence per claim. A finding accepted or rejected without citing a specific contribution anchor (e.g., a `#<phase>-<role>-<N>` anchor), commit SHA, or file path is a narrative dismissal. Narrative dismissal is not a valid finding form and is rejected at seal.

**Maintainer check:** `seal-verification.md` step that evaluates reviewer findings must verify each finding names at least one anchor or path before accepting the finding block. Any finding block that passes without such a citation is a defect in the seal gate.

**17. Success requires coverage of chartered deliverables**

A seal verdict of `success` is rejected unless every item in the collab's `charteredDeliverables` list (declared in the moderator's Audit block) is covered by at least one cited committed path in the execution record. Scope-staging — deferring chartered work to a follow-up collab without explicit moderator re-chartering via a new `(collab init)` — is not a valid closure path and is rejected at seal.

**Maintainer check:** When `charteredDeliverables` is non-empty, `seal-verification.md` must cross-reference each item against `execution.<role>.touchedPaths` before emitting a `success` verdict. A success verdict emitted without this check is a defect.

**Path-not-content caveat:** This gate checks path coverage — that at least one committed path is cited for each chartered item — not content sufficiency. Whether the committed content actually fulfills the chartered item is a reviewer judgment, not a gate outcome. A passing coverage check is a necessary prerequisite for `success`; it does not guarantee correctness.

For source-decomposition work, a chartered path alone is not a completion proof. The Action Plan must pair the path with a measurable content assertion — for example a symbol-placement audit, local-definition ceiling, byte-identical render gate, or dispatch-only check — so the seal can verify that the extraction changed the intended ownership boundary rather than only touching the named file.

**Reopen carry-forward caveat:** Reopen carry-forward coverage is content-validated against `HEAD`; a carried chartered path that is removed or whose content has drifted is dropped from the coverage aggregate, so a name-only carry cannot mask a reverted deliverable. See Invariant #21 for the full carry-forward rule and `reopenCoverage` lifecycle.

**18. Item tags required; `[defer]` rejected**

Action Plan items must carry one of the recognized item tags immediately after the role label: `[execute]`, `[doc-fix]`, `[verify]`, `[precondition]`, `[verify-precondition]`, or `[verify-objective]`. Items carrying `[defer]` or no recognized tag are malformed. Deferral belongs in the `restoreReason` field or a follow-up collab opened via `(collab init)`, not in the Action Plan checklist.

**Enforcement note:** Tag-level validation is enforced by `validate_action_plan_shape()` (`commands/collab/engine/registry.py:3161`) calling `action_plan_item_tag()` (`commands/collab/engine/registry.py:612`): `speak-render` rejects unrecognized or missing item tags; the Action Plan close path's `validate_action_plan_executable_scope()` (`commands/collab/engine/registry.py:3196`) rejects plans without at least one `[execute]` item.

**19. `charteredDeliverables` is optional; coverage gate applies only when declared**

`charteredDeliverables` is an optional moderator declaration. When present in the Audit block, the seal-time coverage gate (Invariant #17) verifies that every chartered item is covered by a cited committed path. When absent — as is correct for discovery and audit collabs where scope is determined by the process, not before it — Invariant #17 is a no-op.

The purpose of `charteredDeliverables` is to prevent reviewer-driven scope expansion at seal: a reviewer finding cannot charter new work. `charteredDeliverables` was never intended to require moderators to enumerate file paths before the audit has run.

**Enforcement note:** Seal-time coverage is enforced by `assert_chartered_deliverables_covered(entry, transcript)` in `commands/collab/engine/registry.py`. No advance-time gate exists; the Conclusion → Action Plan transition is not blocked by the presence or absence of `charteredDeliverables`.

**20. Seal verification is content-addressed, not commit-reachable**

Seal integrity is enforced by the **scope digest** — the `pathDigests`/`contentDigest` recomputed from the *content* of each execution `touchedPath` at `HEAD` — together with the requirement that every touched path is committed at `HEAD` (`SEAL-GIT-STATE` / `SEAL-CONTENT-INCOMPLETE`). The commit SHA recorded in `execution.<role>.commits` is provenance **metadata only**: it is never checked for reachability or membership. A "wrong", orphaned, amended, rebased, or squashed commit does **not** fail the seal, as long as the touched-path content is committed at `HEAD` and matches the sealed digest. No commit-reachability check (`SEAL-PROVENANCE`) exists; content identity is invariant under history rewrites that preserve the tree.

**Reviewer directive:** Never block or condition a seal on commit-hash provenance (e.g. "the cited commit does not contain the file", "the SHA is stale/orphaned"). The only seal-time integrity questions are: (1) is every touched-path's final content committed at `HEAD`, and (2) does the recomputed scope digest equal `verificationSeal.contentDigest`. If both hold, provenance is satisfied regardless of which commit is cited.

**Enforcement note:** Enforced by `invalidate_seal_on_content_drift` and `assert_execution_touched_paths_in_git_state` in `commands/collab/engine/registry.py`; see the [Content-integrity gate](../seal-verification/index.md#content-integrity-gate) note in `(collab seal verification)` and `verification.md` §"Seal time". `repair-execution-provenance` repoints commit metadata and recomputes the digest — it does not make the SHA a seal gate.

**21. Reopen carry-forward coverage is content-validated**

When `(collab reopen)` is called, `reopen_collab` saves the current covered paths — active entries plus any surviving carry from prior reopens — into `reopenCoverage` before clearing execution state. At seal time, `valid_carried_execution_entries` re-checks each saved entry against `HEAD`; paths deleted or changed since the save are dropped. Surviving paths are added to `touchedPaths` and the content-digest set (Invariant #20). Without this re-check, a deleted file could still appear covered at Invariant #17; the implementation prevents this.

**`reopenCoverage` lifecycle:** Written when there are entries to save (`{ createdAt: ISO-8601, executionEntries: object[] }`). Each reopen re-saves active entries plus surviving carry from prior rounds, so coverage accumulates across reopens — re-checked against `HEAD` each time. If no entries exist at reopen time, `reopenCoverage` is not written; a stale value may persist but is overwritten on the next reopen that has entries. Not cleared after close. `reopenCoverage` is consulted at every seal by `valid_carried_execution_entries`. A stale snapshot cannot inflate coverage: each carried path must (a) still resolve at `HEAD` with a matching content-digest and (b) not already be an active execution path. A path whose blob is absent or drifted at `HEAD` is dropped — so a stale snapshot can only 'cover' a deliverable that genuinely still exists at `HEAD`.

**Maintainer check:** Retained coverage lives in `tests/commands/collab/modules.test.sh` for the carry-forward content filter and `tests/commands/collab/registry.py/verification-reopen-rerun-flow.test.sh` for the flow-level reopen/re-execute/re-seal path. Any change to `valid_carried_execution_entries` or the `reopen_collab` snapshot logic must preserve four behaviors: (1) **preserved** — prior path still at `HEAD` remains carried; (2) **drifted** — prior path content changed after the snapshot is dropped; (3) **transitive** — a surviving carried entry remains valid across a later reopen snapshot; (4) **removed** — prior path deleted from `HEAD` is dropped.
