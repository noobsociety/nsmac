# Platform design doctrine

Per-design rules that have been deliberated and converged through the collab process. Each entry is a binding ruling, not a guideline; a departure requires a new collab or an explicit supersession note.

**Scope.** Mechanical enforcement gates (`audit-*.py` scripts, lint rules, CI checks) that implement an already-recorded doctrine decision do not themselves require a separate doctrine entry. The ruling that motivated the gate is the authoritative record; the gate is evidence the doctrine is being honored, not a new deliberation.

---

## Explicit values in records

**Explicit values in records.** Opinionated defaults are a write-time convenience, not a read-time contract. Every resolved default must be stamped into the record at write time and read directly from the stored field — never re-derived from its absence via `.get(key, DEFAULT_*)` or `value if key in object else DEFAULT_*`. Records that carry `createdAt` must declare the field; records without `createdAt` are grandfathered. A lint rule forbids both `.get(<default-key>, DEFAULT_*)` and `... if <key> in <object> else DEFAULT_*` in engine code. Open-roster effort is exempt because it is matrix-resolved advisory state from `agent-effort.json`, not state owned by an individual registry record. `registry.schema.json` is reference/projection only; a parity gate asserts that the schema-declared field set matches the live validator's enforced set.

**Source:** collab `2026-06-09-explicit-values-no-implicit-defaults` (directive: "the principle that values should be explicit"; convergence: 2026-06-09)

---

## JSON registry as state store

**JSON registry as state store.** The platform represents collab lifecycle state as a JSON registry file (`registry.json`) in the user-scope collab state root. The JSON format favors machine readability, deterministic serialization, and inspection without tooling. The companion Markdown transcript is the human-readable ledger; neither substitutes for the other. Registry and transcript are co-evolved by helper writes and must remain reconcilable against each other.

**Source:** collab `2026-06-18-doctrine-naming-glossary-system-reference` (convergence: 2026-06-18)

---

## Markdown transcripts as human ledger

**Markdown transcripts as human ledger.** Collab transcripts are stored as Markdown files (`records/*.md`) alongside `registry.json` in the user-scope collab state root. The transcript is the human-facing reading copy; the registry is the authoritative state. Transcript metadata (status, phase, turn order) mirrors registry fields rather than being independently derived.

**Source:** collab `2026-06-18-doctrine-naming-glossary-system-reference` (convergence: 2026-06-18)

---

## MCP boundary

**MCP boundary.** The MCP (Model Context Protocol) surface is explicitly out of scope for this platform. The `dotcursor` framework routes through `~/.cursor/commands/` dispatch; platform tooling does not depend on or configure MCP endpoints. MCP integrations are application-layer concerns and belong outside the portable layer declared in `platform/standards/framework-boundaries.md`.

**Source:** `platform/standards/framework-boundaries.md`; collab `2026-06-18-doctrine-naming-glossary-system-reference` (convergence: 2026-06-18)

---

## Single-writer helper

**Single-writer helper.** A single Python helper entrypoint (`commands/collab/engine/registry.py`) owns every write to the registry and transcript. Its implementation delegates through the compatibility core (`commands/collab/engine/registry_core.py`) into focused domain leaves; write paths that cannot import the core receive the core-owned commit primitive through an explicit configure seam. No route, agent, or external script writes registry JSON or transcript Markdown directly. The helper ensures consistent serialization, revision tracking, stale-write detection, and digest computation across all collab operations.

**Source:** collab `2026-06-18-doctrine-naming-glossary-system-reference` (convergence: 2026-06-18)

---

## Thin registry core

**Thin registry core.** `registry.py` is the single-writer helper entrypoint (see **Single-writer helper** above). Its thin-core target restricts what belongs in `registry.py`: package bootstrap, compatibility exports, and executable delegation only. Domain logic — field validation, schema migration, I/O operations, seal computation, transcript parsing, plan-item extraction, lifecycle state machines — belongs in owning modules (`registry_io.py`, `seal_verification_logic.py`, `seal_verification_render.py`, `transcript_readers.py`, `registry_constants.py`, and the focused command leaves), not inlined in `registry.py`. A function in `registry.py` that carries business logic is a thin-core violation.

**Verification contract:** A change satisfies the thin-core target when: (a) `registry.py` has no domain helper definitions; (b) the CLI still executes through `registry.py`; and (c) every extracted function lives in its owning module, with `registry_core.py` limited to the keeper set below. The target is not only a line-count threshold; it is a structural gate — domain functions belong where the domain is owned.

**Current state:** `registry.py` is a thin executable facade and the extraction reached its target end-state. `registry_core.py` is the keeper set only: argv dispatch (`build_parser`, `main`), the permanent seal facade pair (`invalidate_verification_seal`, `participant_verify_render`, `render_seal`), the thin `validate_registry` wrapper, the two injected write primitives (`commit_registry_and_transcript`, `commit_new_collab_artifacts`), the narrow orchestration wrappers (`record_execution`, `advance_phase`), and `render_registry_cli_doc`. Further work is boundary maintenance: new command handlers and domain logic land in owning leaves, not in the core.

**Source:** collab `2026-06-29-coding-principles` (directive: "thin core + de-braid completion effort"; convergence: 2026-06-29)

---

## Human-only moderator

**Human-only moderator.** The moderator role is human-owned. Agents may not generate moderator content; every moderator `(collab speak "<message>")` requires human-authored text supplied as the `<message>` argument. The enforcement boundary is `speak.md` step 9; the configuration constant is `registry_constants.py:19–28`. Human-only authorship prevents agents from both posing and framing the discussion structure, preserving the collab as a genuinely human-directed deliberation and eliminating the risk of agentic feedback loops in phase transitions and close verdicts.

**Source:** collab `2026-06-18-doctrine-naming-glossary-system-reference` (convergence: 2026-06-18)

---

## Reopen as full reset

**Reopen as full reset.** `(collab reopen <action-plan|handoff>)` performs a complete phase reset before any contributor re-speaks: status, phase, turn order, completion sub-state, stale seal state, and verdict are all cleared. Partial resets via `(collab set active-phase --force)` are prohibited; `(collab reopen)` is the only registered restore primitive. Full reset prevents silent coverage gaps from persisting across reopen rounds.

**Source:** collab `2026-06-18-doctrine-naming-glossary-system-reference` (convergence: 2026-06-18)

---

## Schema posture

**Schema posture.** `registry.schema.json` is reference and editor-tooling only. `load_registry()` validates through `REGISTRY_VALIDATOR` (the Pydantic validator in `registry_io.py`), not through the JSON schema. A parity gate (`tests/commands/collab/registry.py/registry-schema-roundtrip.test.sh`) asserts that the schema-declared field set matches the validator's enforced set. Load-time JSON-schema enforcement is deliberately not taken; promoting JSON Schema to a second runtime enforcer would create two independently-evolvable enforcement surfaces that can diverge in edge cases and produce split-authority failures. Pydantic is the single live validator; JSON Schema serves the editor-tooling and reference role it was designed for; the parity gate provides equivalent drift protection without runtime cost.

**Source:** `registry.schema.json` (`x-dc-validatorParity`); collab `2026-06-18-doctrine-naming-glossary-system-reference` (directive: "F7 schema-enforcement posture settled by decision"; convergence: 2026-06-18)

---

## Verification three-plane separation

**Verification three-plane separation.** `Completion.verification` is organized into three ordered planes, each certifying a distinct question. `verification.participant` is self-administered remediation: the certifying question is whether the owning role has self-audited and remediated its own write scope. `verification.seal` is content-integrity: the certifying question is whether the transcript content matches the committed tree at `HEAD`. `verification.assessment` is goal truth: the certifying question is whether the stated discussion goal was achieved.

The three planes are not redundant because they answer different questions at different scopes. Passing the participant plane does not confirm that content is committed; passing the seal plane does not confirm the goal was met; passing the assessment plane presupposes both but cannot substitute for either. The participant plane is the sole production round-earning event when enabled; when disabled (`--no-participant-verification`), no production path earns the round and the zero-round seal gate blocks the seal. Canonical mechanics: [`verification.md` § Round definition](../../commands/collab/reference/verification.md#round-definition); disabled-path limitation: see the `--no-participant-verification` guardrail in [`(collab init)`](../../commands/collab/init/index.md).

**Revision coupling:** The disabled-path claim above, the `--no-participant-verification` guardrail in [`(collab init)`](../../commands/collab/init/index.md), and the Round-earning event note in [`(collab participant verify)`](../../commands/collab/participant-verify/index.md) are a coupled set; when a production round-earning path for the disabled posture lands, all three must be revised in the same change or the docs contradict the code. **Current state:** no production path earns a round when `--no-participant-verification` is set; `participant_verify_render` is bypassed and `verification.rounds` stays at 0; the zero-round seal gate blocks the seal. The gate has not yet fired. Verification: search for any code path that both (a) is reachable when `participantVerification == false` and (b) calls `participant_verify_render` or otherwise increments `verification.rounds`; any such path is a gate trigger.

**Source:** collab `2026-06-26-redundant-participant-verify` (directive: "settle the fate of `Completion.verification.participant`"; verdict: not redundant; convergence: 2026-06-26)

---

## Present-tense doctrine: closed-collab provenance carve-out

**Present-tense doctrine: closed-collab provenance carve-out.** The present-tense-only principle ("the present tense is global") governs live, forward-facing description of system state: a doc must say what the system currently does, not what it used to do or will someday do. It does not extend to content whose subject is itself a past event — a closed collab's outcome, a retired mechanism's tombstone, a superseded registry value kept for forensic reference. Describing a historical fact in the past tense is not a present-tense violation; describing current system behavior in the past tense is. `invariants.md` #1's retention of the `dp` role key "as a backed tombstone for historical-participant rendering of closed collab `a13dba4c`" and `agent-id.md`'s note that "existing versioned registry values remain historical records and must not be migrated" are instances of this carve-out, not exceptions to the present-tense rule.

This entry settles only the collision raised in the reviewer's second finding at conclusion — the global tense directive read against the retained `dp` tombstone — so the two no longer read as contradictory. It does not charter a repo-wide present-tense sweep: the reviewer's first finding holds that such a sweep is unchartered work requiring its own `(collab init)` (Invariant #19), and that remains true; this entry neither performs nor authorizes it.

**Source:** collab `2026-06-30-completely-remove-gemini-agent-and-everything-related-to-it-from-this-system` (moderator directive, 2026-06-30 22:10: "the gemini removal is scoped, the present tense is global"; reviewer findings at conclusion, 2026-06-30 22:17). Recorded as a direct ruling per operator decision rather than through a new collab convergence — the reviewer flagged the gap twice without a follow-up collab being opened; the operator chose to resolve the logical collision by ruling instead.
