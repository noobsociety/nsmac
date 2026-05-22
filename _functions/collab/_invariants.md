# Cross-route invariants

Cross-route rules that apply to every route under `commands/collab` and the `tools/collab/registry.py` helper. Any future route or helper change must stay consistent with all clauses below.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab invariants, cross-route collab rules, agent-honor-system, collab lifecycle notices

## Steps

1. Read this document when changing any collab route or `tools/collab/registry.py` helper behavior.
2. Verify the changed route or helper stays consistent with all notes below.
3. Do not mutate registry state from this documentation-only reference.

## Notes

**1. Route prose as contract; helper as enforcement (`agent-honor-system` clause)**

Route prose declares the contract. The helper enforces it. Every documented ABORT in a route file maps 1:1 to a helper subcommand check, or is explicitly marked `agent-honor-system` in the route notes to signal it relies on agent judgment rather than runtime enforcement.

Free-text tokens are literal content. A route argument such as a title, label, message, or routing-only dispatch token is never work to execute unless the route explicitly defines an execution phase for that content.

Inline marker form: `**ABORT** (agent-honor-system): ...` placed on the same line as the ABORT clause it exempts. The marker exempts only the ABORT clause on the line it appears in — it does not exempt subsequent or sibling clauses. This file is the single source of truth for this grammar; the detector enforces line-level binding.

Anchor convention: each ABORT in `<route>.md` must carry a stable id anchor `<!-- abort: <id> -->` on the line immediately above it. The anchor id must start with the route stem followed by a hyphen (e.g., `speak-` in `speak.md`); the detector enforces this prefix and rejects anchors that omit it.

Maintainer check: `git grep -rn 'agent-honor-system' _functions/collab/` shows every agent-honor-system clause. Any undocumented ABORT that has neither a helper check nor this marker is a defect.

Maintainer check: `git grep -rnP '(?<![A-Za-z0-9_])(mod|pa|pe|tw)(?![A-Za-z0-9_])' -- '*.md' '*rule file'` is the broad review sweep for role-key prose drift. Every prose match must either be covered by the documented carve-outs in `tools/command-system/audit-role-prose.sh` or rewritten to function-bound prose.

**2. Registry as source of truth; transcript as human ledger**

The resolved registry (`$HOME/.collabs/<projectId>/registry.json` by default, or the explicit `--registry` path) is the authoritative source for command state. The transcript (`records/*.md` inside the resolved state root by default) mirrors selected metadata and captures human-readable context. Registry-only mutations — `/collab set`, `/collab unset`, moderator removal in `speak-lifecycle-live` — must remain reconcilable against transcript-readable state. No registry write may create state that cannot be explained or confirmed from the transcript.

**3. Phase-transition notices as structured helper output**

Phase-transition notices and terminal lifecycle notices are emitted by helper paths (`speak-lifecycle-live`, `advance_phase`, `close_collab`, `archive_collab`) as structured JSON records. Route docs describe that output; they do not reimplement or freestyle the decision. Free-form prose copied across route files to describe transition behavior is a defect.

Structured notice shapes:
- `{"notice": "compact", "transition": "Discussion->Conclusion", "message": "..."}` — emitted at Discussion → Conclusion.
- `{"notice": "subagent", "transition": "Handoff->Completion", "message": "..."}` — emitted at Handoff → Completion.
- `{"notice": "clear", "status": "<closed|archived>", "message": "..."}` — emitted after close or archive.

**4. Disk-state authority**

Conversation context is cache; disk state is truth. The resolved registry and transcript files are the authoritative sources. Helpers recompute state from files, not from agent memory. This is the durability invariant that makes collabs survive `/compact`, `/clear`, agent swaps, and harness restarts equally.

**5. Context-changing events**

The following six events are context-changing: `/compact`, `/clear`, agent swap mid-collab, subagent return, phase transition (`advance`/`restore`), and successful concurrent write by another participant. After any of these events, the route helper of record must be re-run before any registry or transcript write — `speak-state` for `/collab speak`, `execute-spawn` for each subagent spawn under `/collab run plan`, and the gate helper named in each route's playbook for other routes. An agent must never trust prior helper output after a context-changing event.

**6. Subagent write-scope disjointness**

When a parent agent spawns a subagent for implementation work (e.g., during `/collab run plan`), the parent must declare a disjoint write scope before spawning. The parent rejects any returned patch that touches paths outside the declared scope. A subagent must never become the author of a collab turn, and must not mutate registry or transcript state independently.

**7. Non-goal**

Collab routes do not orchestrate `/compact`, `/clear`, or subagent spawning. Those are harness concerns. Route files document survivable state and safe lifecycle points; the harness decides when to evict.

**8. Caller-asserted role identity**

The collab system records the role under which an agent joins (`participants[].agentId`) but does not authenticate the caller of any subsequent helper invocation. A role key passed to `tools/collab/registry.py` is caller-asserted. The system enforces lifecycle rules (turn order, one-speak phases, reviewer gates, phase advancement) over caller-asserted identity; it does not enforce that the declared role matches the actor at the harness layer.

**Maintainer check:** Routes that present a role check as a security boundary are mis-stating the model. Where a route note implies enforcement, it must instead cite this invariant and describe the lifecycle effect of a violation, not a prevention claim. `git grep -rn 'trust-model' _functions/collab/` identifies candidates for review.

**9. Action Plan checklist shape**

Every Action Plan contribution must consist entirely of flat checklist assignment lines after exempt content is removed. This invariant clause is the canonical source for shape enforcement; `speak.md` step 10 and the `Action Plan checklist shape` note, `_contribution-budget.md` `action-plan-checklist` row, and `rewrite-speak.md` all cite this invariant and do not paraphrase it.

**Canonical regex:** `^- \[[ x]\] \*\*[a-z]+:\*\*` (case-sensitive; `[a-z]+` matches the role key)

**Pre-pass order** (strip before applying the regex):
1. HTML comments (whole block, including the rendered `<!-- collab:effort-override … -->` form)
2. Blank lines
3. Markdown headings (`#` through `######`)
4. `EFFORT OVERRIDE:` first-line literal (the raw override declaration)

**ABORT anchor:** `speak-render-action-plan-shape`

**Shared validator:** A single validation function applies this pre-pass and regex. `speak-render` and `rewrite-speak` both invoke it; it activates only when `activePhase == "Action Plan"` and aborts before any transcript, header, or registry mutation.

**Abort message templates (verbatim):**

Shape-violation: `ABORT: line N does not match Action Plan shape '- [ ] **<role>:** ...' (Invariant #9, _invariants.md). Offending line: '<line>'. Example: '- [ ] **tw:** Update the route doc.'`

No-assignment-lines: `ABORT: Action Plan body contains no assignment lines after exempt content is removed (Invariant #9, _invariants.md). Example: '- [ ] **tw:** Update the route doc.'`

**Test file:** `tests/tools/collab/registry.py/speak-render-action-plan-shape.test.sh` — three cases: prose header, plain bullet, empty-after-exempts. Each case asserts the full ABORT message text, unchanged transcript bytes, and unchanged registry phase.

**Forward-only:** Historical contributions are not re-validated. Role-token vocabulary remains in the `run plan` parser; this gate enforces shape only.

**10. Rollback triggers**

Observable-event conditions derived from the 2026-05-18 missed-and-deferred-goals audit. Each line names the observable event that re-opens the item; no behavior change until the event fires.

- **Item 7 (round-counting / budget-exempt assessment path after cap-exit):** if any seal-attempt transcript exceeds 18 turns, or two consecutive participant verifications fail with full-body blocks present, open a follow-up audit of the round-counting and budget-exempt assessment path.
- **Item 9 (`/collab rewrite-execution` redesign):** if any seal-attempt transcript exceeds 12 turns, open a follow-up DX audit on `rewrite-execution` and turn-budget management across `/compact`.
- If any reviewer-backed collab closes via `--cap-exit archive` on a clean first seal (no findings during participant verification), open a verification-cap audit. *(Fired: collab #16, 2026-05-18. Resolved inline: root cause was doc gap on archive semantics + reviewer soliciting verdict from user instead of determining it autonomously. Fixes: `seal-verification.md` and `_verification.md` updated to prohibit `--cap-exit archive` on clean verification and to require autonomous verdict determination. Detection remains active.)*

**11. Observation backlog**

The following carry-forwards from the 2026-05-18 missed-and-deferred-goals audit are observation-class: no behavior change until the named event is observed. Each re-enters only on evidence, not on transcript memory.

- **Item 10 (`_tests/_roles.md` generator):** re-entry when a fifth role is added to the roster.
- **Item 11 (effort-matrix shape redesign):** re-entry if a third axis (admission column or `level|null` cells) surfaces during Action Plan drafting.
- **Item 12 (cross-project registry federation):** re-entry when more than one project store in `~/.collabs/` shows observable drift.
- **Item 13 (stub retirement observation point):** re-entry when a coverage assertion is added confirming stub fallback is unreached on resolution.
- **Item 14 (PE Q4 carry-forward — pre-seal reopen primitive):** re-entry if a future protocol redesign reopens the pre-seal flow.
- **Item 15 (CI scope items — required-status checks, secrets, deploy gates):** re-entry when merge-gating, authenticated workflows, or a deploy surface is introduced.

**12. Routing-vs-rationale lifecycle**

When a structured field is cleared on consume (e.g., during a phase restore transition), classify it before the transition:

- **Routing field:** directs where the workflow goes next (e.g., `restoreTarget`). Cleared on consume is correct; the routing decision has been executed.
- **Rationale field:** explains why the transition is happening (e.g., `restoreReason`, `evidence`, `failureCategory`). Must be emitted to a durable surface atomically with the write that creates the field, not at the consume site that clears it.

**Write-time emission rule:** a rationale field needed by downstream actors after a transition must appear on a durable surface before or at the same write that first records it. The audit log is the canonical durable surface for collab-scoped cause. A marker that the event occurred is not sufficient; the rationale content must be present.

**Diagnostic frame:** for any transition that clears structured state, verify: (1) which cleared fields are routing (cleared on consume is correct); (2) which are rationale (require a write-time durable emission); (3) whether the durable surface carries the content, not merely a marker.

Maintainer check: `grep -rn 'restoreReason' tools/collab/` enumerates verdict-write candidate sites. Each non-success verdict write path must have a paired durable rationale emission in the same atomic operation.
