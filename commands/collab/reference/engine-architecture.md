# Engine architecture

Boundary map for the collab engine: module roster, facade pattern, DI constraint, decomposition status, keep-whole decisions, and forward extraction gates.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** engine architecture, engine modules, registry decomposition, facade pattern, DI boundary, keep-whole decisions, extraction gates, module roster, seal boundary, render boundary

## Steps

1. Read this document when auditing engine module boundaries, planning extractions, or evaluating the DI constraint.
2. For `registry_state.py` public entry, state-root resolution, and project-identity binding, see [registry-state.md](registry-state.md).

## Notes

### Facade and DI boundary

`commands/collab/engine/registry.py` is the permanent CLI facade. It is the single importer of all extracted modules; the modules do not import each other. Dependencies flow in one direction: registry.py calls into extracted modules as pure functions or passes state as arguments. No module-level or global state is shared between extracted modules.

The facade owns: CLI argv dispatch, high-level orchestration wrappers (`render_speak`, `render_re_speak`, `render_seal`, `render_status`, `render_participants`, `render_registry_cli_doc`), and the `render_seal` permanent dispatch shim. All managed rendering, seal-integrity logic, and contribution validation belong to their extracted modules.

### Module roster

21 extracted modules in `commands/collab/engine/`:

| Module | Owns | Does not own |
| --- | --- | --- |
| `errors.py` | shared exit helpers | any registry dependency |
| `registry_constants.py` | registry lifecycle vocabulary and policy constants | state I/O |
| `registry_state.py` | project-identity binding, state-root resolution | registry reads/writes |
| `dispatch_forms.py` | command dispatch notation rendering | state, I/O, registry |
| `planned_routes.py` | route prerequisite validation, issue-bridge detection | phase mutation |
| `transcript_readers.py` | transcript phase parsing, contribution-block extraction, transcript-path resolution and per-entry reads | rendering or writes |
| `normalizers.py` | slug/title/path/scope normalization | state, I/O |
| `digests.py` | content/path digest computation and signatures | git policy |
| `handoff_shape.py` | handoff writeScope/validationCommands schema | lifecycle |
| `git_repo.py` | git subprocess reads: head, commits, content-at-ref | seal policy |
| `registry_io.py` | registry persistence, lock, resolve; validator injection | phase decisions |
| `participants.py` | participant roster, reviewer wiring, turn-order helpers | phase mutation |
| `phase_lifecycle.py` | phase sequencing, phase advancement, and lifecycle notices | registry mutation, rendering |
| `execution.py` | execution checks, run-plan support, write-scope enforcement, execution state recording | seal |
| `contribution_store.py` | contribution-store path and shape helpers | registry state, rendering, write path |
| `contribution_validation.py` | speak-time contribution gates, moderator contribution normalization | rendering, write path |
| `diff.py` | read-only collab drift comparison | registry writes, rendering, state mutation |
| `registry_validation.py` | schema validation | advisory math, write path |
| `effort.py` | advisory math | schema validation, write path |
| `transcript_render.py` | managed rendering: header, TOC, all `<details>` blocks, contribution blocks, effort-override banners | registry state, phase lifecycle, write-path dispatch, CLI entry-point logic |
| `seal_verification.py` | seal state, stale-seal triggers, content-integrity gates, participant-verify state and rendering, verdict construction, assessment rendering, cap-exit dispatch, chartered-deliverables coverage, seal rendering | registry persistence, phase lifecycle, participant roster management, non-seal transcript rendering, CLI dispatch |

### Decomposition status

All 6 extraction stages are complete:

1. Pure readers and parsers — done (#56: normalizers, digests, handoff\_shape, git\_repo, registry\_io)
2. Route-planning helpers — done (#56: participants, phase\_lifecycle, execution, dispatch\_forms)
3. Managed rendering engine — done (#57: transcript\_render.py)
4. Seal/verification engine — done (#58: seal\_verification.py)
5. Speak-time contribution validation — done (contribution\_validation.py, contribution\_store.py)
6. Registry validation, effort math, and drift comparison — done (registry\_validation.py, effort.py, diff.py)

The decomposition is complete. `registry.py` is the CLI facade plus thin orchestration wrappers; all modules in the roster above own their respective domains and no further extractions are planned. The facade's remaining surface is CLI argv dispatch, high-level orchestration calls into the extracted modules, and the `render_seal` dispatch shim.

### Keep-whole decisions

**`seal_verification.py` (kept whole — verification boundary):** All seal integrity, stale-seal triggers, content-integrity gates, participant verification, and verdict construction are cohesive and mutually dependent. Splitting them would either introduce circular imports or fragment the integrity guarantee across modules. This module may only be imported by `registry.py`.

**`transcript_render.py` (kept whole — managed-rendering boundary):** Header scaffolding, TOC management, and all `<details>` block construction share the `rendered_collapsible_block` primitive and the single-owner invariant: no caller constructs a `<details>` block outside this module. Splitting prematurely would compromise that invariant. If the module later warrants division, the documented split boundary is: `header_render.py` (header, TOC, `insert_toc_entry`) and `contribution_render.py` (contribution/collapsible-block rendering, excerpt/full-body handling, effort-override banners).

### Forward extraction gates

Every future extraction item must satisfy all three gates before merging:

**[P1-render]** Byte-identical render gate: any item touching managed rendering (participants table, TOC, header, `<details>` scaffolding) must run the rendering helper before and after against a fixed fixture transcript and assert a zero-byte diff. Prose "behavior-equivalent" review does not satisfy this gate. Rationale: one whitespace byte of render drift silently breaks every route asserting managed-section bytes (Invariant #1).

**[P2-seal]** Paired staleness-test gate: each stale-seal trigger relocated during a seal/verification extraction must ship a shell test asserting the trigger still invalidates the seal after the move. Rationale: a seal that "appears valid but covers different evidence" is a silent failure; this gate makes it loud.

**[V-shape]** Per-item guardrail packet (must appear in every extraction collab's Action Plan): source cluster, destination module, public imports retained by `registry.py`, byte-identical render assertions where [P1-render] applies, and write-path freeze confirmation.

Commit discipline: each extraction item lands as its own atomically-scoped, accurately-titled commit. Bundling a design move with behavioral assertions in one commit mislabels the record; git history is the canonical record of past outcomes.

### Directive of record

"Keep splitting the oversized registry core into focused, independently testable parts. One enormous module is hard to reason about and risky to change; cohesive units shrink the blast radius of every edit."  
— Collab 2026-06-04-registry-decomposition

*Promoted from the `registry.py` header, which now carries a pointer to this file.*
