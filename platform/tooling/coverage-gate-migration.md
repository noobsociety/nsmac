# Coverage Gate ABORT-Coverage Record

This file records the burn-down of historical ABORT-clause debt in
`platform/tooling/coverage-gate.sh` and the resulting present-state posture.
All historical public collab route ABORT clauses were migrated from prose to
anchored, test-backed (or `agent-honor-system`-marked) clauses across six
batches completed 2026-06-24; that burn-down is the foundation the current
opt-in posture builds on. The current mandatory/opt-in coverage-gate contract
itself is specified in `REPOSITORY.md`, not restated here.

## Present State

- allowlisted unanchored clauses: 0
- discovery-debt unanchored clauses: 0
- unknown unanchored clauses outside those buckets: 0

The burn-down target of zero allowlisted and zero discovery-debt clauses was
reached, and the allowlist file and the `DISCOVERY_DEBT_ROUTE_FILES` symbol
have both been removed from the codebase. On top of that zero-debt baseline,
`coverage-gate.sh` now proves the mandatory behavior-smoke floor for every
route and reports opt-in per-clause anchor/test coverage for the
reviewer-selected keep-list; it is no longer a full-exhaustive,
P9-required-for-every-clause gate.

## Classification

Each batch classified ABORT clauses into one of three buckets before anchoring:

- **Test-worthy:** helper-enforced or helper-verifiable abort paths. Each received
  a stable `<!-- abort: <route>-... -->` anchor and a P9 test or central checker row.
- **Reclassify or remove:** route prose that is advisory, duplicated by a more
  specific abort, or already covered by an `agent-honor-system` clause. These
  were rewritten, removed, or explicitly marked per
  `commands/collab/reference/invariants.md`.
- **Untestable by design:** clauses that depend on harness judgment or host state
  unavailable to repo-owned tests. These cite the reason and use the
  `agent-honor-system` marker.

### Tier analysis — starting classification (87 allowlisted clauses)

Enumerated during the structural-architecture-completion-audit (pe). No untestable
clauses were in the allowlist — all 87 were deferred fixture work, retired across
Batches 1–6. This is the same 87-clause count the Burn-Down Record below
reconciles against the six batch totals; the Tier breakdown immediately below
(~35 + ~20 + ~15 + ~17 ≈ 87) accounts for it by fixture complexity, and the
26 discovery-debt clauses retired in Batch 6 are a separate bucket, not part
of this count.

**Tier 1 — Shared structural guards (~35 clauses, lowest fixture complexity):**
`record-unreadable`, `registry-target-unavailable`, and `record-is-closed` appear
across ~15 routes each. One test per unique failure mode per route suffices.
`Registry targeting` Notes-section ABORTs duplicate the matching Steps ABORT for
the same failure mode — assign the same anchor name and one test covers both.

**Tier 2 — Phase/state guards (~20 clauses, moderate complexity):**
`active-phase-missing`, `phase-not-completion`, `no-next/prev-phase`,
`completion-block`. Require valid registry state with specific `activePhase` values.

**Tier 3 — Role/permission guards (~15 clauses, low-to-moderate complexity):**
`role-file-unreadable`, `invalid-role-JSON`, `role-not-registered`,
`moderator/reviewer-removal-block`, `field-not-settable/unsettable`.

**Tier 4 — Data/logic guards (~17 clauses, highest fixture complexity):**
`no-prior-summary`, `no-prior-execution`, `requires-chain aborts`, `seal-write
write failure`, `turn-order validation`. Require multi-step pre-built state.

**Reclassification resolved:** The two "Recovery path" Notes ABORTs in `advance`
and `restore` describe operator detection of a helper mirror defect after a helper
call returns successfully. They are marked `(agent-honor-system)` and are no
longer migration allowlist debt.

### Test harness layer

Tests live under `tests/commands/collab/registry.py/` as individual `<anchor>.test.sh`
files, each delegating to `admin-guard-case.sh <case-name>`. This is the standing
contract for all Tier 1–3 guards and any Tier 4 guard whose fixture needs one registry
entry plus one helper call:

- **Extend the shared harness** (`admin-guard-case.sh`) with a new `case` block for
  each new anchor. Add per-fixture-class setup helpers (e.g. `set_active_phase`,
  `remove_transcript`) inline rather than creating a sibling file.
- **Add a sibling harness** only when a batch needs a materially different artifact
  model: multi-record state, external issue handoff data, or seal/verification
  evidence chains. Name it `<fixture-class>-case.sh` and follow the same
  delegate-from-thin-test-file pattern.
- **Never add a per-route harness.** One shared dispatcher per fixture complexity
  class is the ceiling. If two guards share the same setup shape, they share the
  same harness.

Established by Batches 1–3; governed Batches 4–6.

## Burn-Down Record

Each batch updated the (since-removed) `coverage-gate-allowlist.txt`, this file's
counts, and the route/test evidence in the same commit. The allowlist was retired
at the end of the burn-down. The live rule is now the opt-in posture specified in
`REPOSITORY.md`: the real-record behavior-smoke floor is mandatory, while
per-clause anchors are kept only for reviewer-selected direct P9 obligations.
No allowlist file exists to add to.

The six batches account for the full starting debt exactly: 13 + 12 + 28 + 19 +
14 + 27 = 113 retired clauses, matching 87 original allowlisted clauses plus 26
discovery-debt clauses. No clause is intentionally left unassigned to a batch.

**Batch 1 — Administrative guards (13 clauses, Tier 1 only; completed 2026-06-24):**
Routes: `activate`, `archive`, `close`, `delete`, `open`.
All clauses are Tier 1 structural guards (record-unreadable, target-not-found,
archived-record). Retired by anchoring the route clauses and adding matching P9
tests under `tests/commands/collab/registry.py/`.

**Batch 2 — Phase-sequence routes (12 clauses, Tier 1 + Tier 2; completed 2026-06-24):**
Routes: `advance`, `restore`.
Retired by anchoring ten helper-enforced phase-sequence and structural guards
with P9 tests under `tests/commands/collab/registry.py/`, and by reclassifying
the two helper mirror-defect recovery checks as `(agent-honor-system)`.

**Batch 3 — Role and field routes (28 clauses, Tier 1–3; completed 2026-06-24):**
Routes: `join`, `remove-participant`, `retract-speak`, `set`, `unset`,
`summarize`.
Retired by anchoring helper-enforced structural, role-state, role-permission,
and field-validation guards with P9 tests under
`tests/commands/collab/registry.py/`. Established the shared-harness fixture
taxonomy recorded in Classification § Test harness layer.

**Batch 4 — Contribution routes (19 clauses, Tier 1–3 + phase guards; completed 2026-06-24):**
Routes: `speak`, `rewrite-speak`.
Retired by anchoring eighteen helper-enforced structural, phase, role-resolution,
turn-order, Completion-phase-block, and one-speak guards with P9 tests under
`tests/commands/collab/registry.py/`, and by reclassifying the `rewrite-speak`
helper-defect clause (step 9 missing-block detection) as `(agent-honor-system)`.
The Completion-phase block is enforced by `speak-render`/`rewrite-speak-render`
(not `speak-state`); one-speak enforcement is exercised by seeding a prior
moderator contribution and pinning the role as the expected speaker so the
duplicate-phase guard fires.

**Batch 5 — Execution routes (14 clauses, Tier 1–4; completed 2026-06-24):**
Routes: `run-plan`, `rewrite-execution`.
Highest fixture complexity; require Completion-phase state. Retired by anchoring
ten helper-enforced structural, phase, role-resolution, and requires-chain
guards with P9 tests under `tests/commands/collab/registry.py/`, and by
reclassifying four clauses as `(agent-honor-system)`. The closed, active-phase
enum, and registry-target guards are backstopped by the `execution` helper
(`record is closed`, `collab activePhase must be one of`, `registry target not
found`); the Completion-phase guard is enforced by `execute-spawn`
(`execute-spawn is valid only in Completion`); role-not-registered is
backstopped by `caller role must already be a participant`; and the
requires-chain "perform or halt" contract is backstopped by the recorder's
unchecked-assigned-item guard (`execution completed blocked for role <role>: <N>
unchecked assigned Action Plan item(s) remain`), exercised with a Tier-4 fixture
that seeds an unchecked `**<role>:**` Action Plan item in Completion phase. The
four `(agent-honor-system)` reclassifications are the two record-unreadable read
guards (`run-plan`/`rewrite-execution` step 2 — the `execution` and
`execute-spawn` helpers tolerate a missing transcript rather than aborting) and
the two `rewrite-execution` Completion-history preconditions (step 7
last-execution-already-succeeded and step 8 no-prior-execution — both read from
transcript prose with no mirrored helper guard). The `rewrite-execution`
registry-target clause was anchored before this batch and is covered by the
`route-doc-contracts` central checker, so it was never allowlist debt.

**Batch 6 — Seal and discovery-debt routes (27 clauses; completed 2026-06-24):**
Routes: `seal-verification` (1 remaining allowlisted clause: seal-write
path) plus the discovery-debt routes from `DISCOVERY_DEBT_ROUTE_FILES`
(`log`, `participant-verify`, `reopen`, `show-verdict`, `status`).
Retired by anchoring all 27 clauses; 24 are backed by new P9 tests under
`tests/commands/collab/registry.py/` (delegated through `admin-guard-case.sh`
with new `init_participant_verify_target` and `seed_failed_verdict` fixtures),
and 3 are reclassified `(agent-honor-system)`
with a reason in the clause: `seal-verification-write-failed` and
`participant-verify-render-failed` (generic non-zero-exit wrappers around
`seal-write`/`participant-verify-render` whose distinct failure modes are
anchored and tested separately) plus one retired-route clause removed with its
route. The `reopen` step-3 invalid-phase guard is enforced by argparse
`choices`, so its test asserts the argparse `invalid choice` rejection. Result:
the allowlist file and the `DISCOVERY_DEBT_ROUTE_FILES` symbol were subsequently
removed. Closes queue row #31
(`backlog/31-collab-audit-coverage-abort-burn-down.md`). Batches 1–5 (allowlist
leg) carry no separate queue row; they trace to row #16 (Tooling contracts,
sealed) plus the weekly-check H4 allowlist target.
