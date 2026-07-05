# Engine architecture

Boundary map for the collab engine: module roster, facade pattern, dependency-injection constraints, boundary decisions, and maintenance gates.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** engine architecture, engine modules, registry decomposition, facade pattern, DI boundary, boundary decisions, extraction gates, module roster, seal boundary, render boundary

## Steps

1. Read this document when auditing engine module boundaries, planning extractions, or evaluating the DI constraint.
2. For `registry_state.py` public entry, state-root resolution, and project-identity binding, see [registry-state.md](registry-state.md).

## Notes

### Facade and DI boundary

`commands/collab/engine/registry.py` is the permanent executable facade. It performs package bootstrap, exposes lazy compatibility imports for tests/importers, and delegates execution to `registry_core.py`/`registry_dispatch.py`. The compatibility core wires only the remaining cycle-blocked callbacks; extracted modules must not import the executable facade. Leaf-to-leaf imports are allowed only when a documented dependency boundary permits them.

The executable facade owns no domain behavior. `registry_parser.py` owns CLI argv shape and generated CLI documentation. `registry_dispatch.py` owns table-driven subcommand dispatch. `registry_io.py` owns commit primitives. `registry_core.py` owns compatibility exports, facade configuration, the participant-verification render facade, the thin `validate_registry` wrapper, and the narrow orchestration wrappers (`record_execution`, `advance_phase`). All command bodies, managed rendering, seal-integrity logic, and contribution validation belong to their extracted modules.

### Module roster

Implementation modules in `commands/collab/engine/` (plus the executable facade `registry.py` and the generated-doc helper `lifecycle-doc.py`):

| Module | Owns | Does not own |
| --- | --- | --- |
| `errors.py` | shared exit helpers | any registry dependency |
| `registry_constants.py` | registry lifecycle vocabulary and policy constants | state I/O |
| `config_paths.py` | default configuration-path resolution: resolve the command config root (honoring the `COMMAND_CONFIG_ROOT` override) and derive the default roles-dir, effort-defaults, agent-model, and flag-taxonomy paths; a standalone leaf with no engine dependencies that self-resolves the repository root | the executable sys.path bootstrap, any config-file reading |
| `flag_taxonomy.py` | flag-taxonomy spec reader: parse the flag-taxonomy reference markdown (per-command headings and pipe-delimited flag rows) and project it into a class-grouped inventory (advisory / helper-enforced / generator-derived), rejecting unknown flag classes; owns the sole-use flag-row pattern and aggregates lower-tier leaves (config_paths, errors) | registry persistence, phase mutation, any write path |
| `source_contracts.py` | source-contract validation command: validate that the registry loads cleanly (no stale lock) and that required source-contract anchors are present across the flag-taxonomy, seal-verification, invariants, and planned-route reference documents under the config root; aggregates lower-tier leaves (config_paths, errors, planned_routes, registry_io) | registry persistence, phase mutation, any write path |
| `help_command.py` | help-route command: resolve a `(help <namespace> <route...>)` token list to its `commands/<namespace>/.../index.md` reference document under the repository root, reject malformed tokens and any path escaping the commands tree, and print the document; aggregates lower-tier leaves (config_paths, errors) | route dispatch, registry persistence, any write path |
| `browser.py` | browser launch: open a URI in the system browser via an injectable opener, capturing any failure (raised exception or falsey "no browser" return) as a human-readable string; a standalone leaf with no engine dependencies | URI construction, registry persistence, any write path |
| `render_commands.py` | transcript render/view/summarize command handlers: re-render the managed header and persist it (`render-status`, `render-participants`), replace the managed phase summary (`summarize`), and emit a single phase section read-only (`transcript-view`) | the two-file commit implementation (`registry_io`), header rendering, summary replacement |
| `field_commands.py` | field and participant mutation command handlers: set or force a single registry field (`set`, including reviewer assignment and the force-only `active-phase` jump), clear the reviewer (`unset reviewer`), and drop a participant from roster and turn order (`remove-participant`); validates via the importable `validate_registry_data` | the two-file commit implementation (`registry_io`), header rendering, registry validation |
| `lifecycle_commands.py` | record lifecycle status-change command handlers: archive a record and clear it as active (`archive`), reopen a closed record (`open`), close a record after enforcing execution and reviewer-seal close gates (`close`), and permanently delete a record with its transcript and contribution store (`delete`) | the two-file commit implementation (`registry_io`), header rendering, the seal verdict companion writer |
| `repair_commands.py` | integrity repair command handlers: mark a transcript repair that may have touched execution evidence (`transcript-repair`), record an out-of-scope patch outside a role's declared writeScope (`out-of-scope-patch`), and repair a completed execution's provenance — work repo, commit ids, content digests, paired signature (`repair-execution-provenance`) | seal-invalidation ownership (`seal_verification_logic`), git provenance helpers, digest computation |
| `reactivation_commands.py` | record reactivation command handlers: restore a record's prior content from a revision event's `_legacyBefore` snapshot (`restore-content`) and reopen a record into Action Plan or Handoff after a non-success Completion verdict (`reopen`); owns the `save_registry_with_event_type` single-file write helper | seal-invalidation ownership (`seal_verification_logic`), two-file commit ownership (`registry_io`), revision-event primitives, registry validation |
| `onboarding_commands.py` | record onboarding command handlers: create a new moderated record with its transcript and contribution store (`init`) and join a role into an existing record's roster (`join`); owns the `ensure_init_project_metadata` init helper | commit primitives (`registry_io`), registry validation, transcript rendering, the init token parser |
| `speak_commands.py` | speak-path command handlers: the auto-advance lifecycle when required roles have contributed (`speak-lifecycle`), set the active record (`activate`), project a role's speak-readiness state (`speak-state`), advance from the live transcript (`speak-lifecycle-live`), append a rendered contribution (`speak-render`), rewrite the latest contribution (`rewrite-speak-render`), and retract (tombstone) the latest active-phase contribution (`retract-speak`) | the two-file commit implementation (`registry_io`), transcript rendering, contribution validation, contribution-store persistence |
| `route_write_guard.py` | route write-path guard (`write-guard`): confirm a route only writes under the user-scope collab state root (the registry file, its lock, and the `records/` transcript tree), rejecting absolute paths and any out-of-root target; the Completion execution path is exempt | registry state, transcript reads, commit primitives — pure path-shape validation |
| `registry_state.py` | project-identity binding, state-root resolution | registry reads/writes |
| `dispatch_forms.py` | command dispatch notation rendering | state, I/O, registry |
| `command_lines.py` | literal `registry.py` CLI invocation strings (RESUME, transcript-view) | state, I/O, registry, dispatch notation |
| `registry_parser.py` | CLI argv shape (`build_parser`) and generated CLI documentation (`render_registry_cli_doc`) | command behavior, registry state, transcript writes |
| `registry_dispatch.py` | table-driven subcommand dispatch and registry-path resolution | parser shape, command behavior, registry schema validation |
| `registry_core.py` | compatibility exports, facade configuration, the participant-verification render facade, the `validate_registry` wrapper, and the narrow orchestration wrappers (`record_execution`/`advance_phase`) | executable bootstrap, parser shape, dispatch ladder, commit primitive ownership, extracted domain ownership, any command body with extractable domain logic |
| `registry_io.py` | registry persistence, schema validation hook, locking, resolution, revision events, and registry/transcript commit primitives | phase or lifecycle decisions |
| `planned_routes.py` | route prerequisite validation hook | phase mutation |
| `transcript_readers.py` | transcript phase parsing, contribution-block extraction, transcript-path resolution and per-entry reads | rendering or writes |
| `normalizers.py` | slug/title/path/scope normalization | state, I/O |
| `digests.py` | content/path digest computation and signatures | git policy |
| `handoff_shape.py` | handoff writeScope/validationCommands schema | lifecycle |
| `git_repo.py` | git subprocess reads: head, commits, content-at-ref | seal policy |
| `participants.py` | participant roster, reviewer wiring, turn-order helpers | phase mutation |
| `phase_lifecycle.py` | phase sequencing, phase advancement, and lifecycle notices | registry mutation, rendering |
| `speak_state.py` | speak-eligibility state model: per-entry speak-state dict and the read-only next-command, next-line, policy-blocker, and phase-summary projections over it | registry persistence, phase mutation, rendering |
| `advisories.py` | post-action/recovery advisory rendering: post-speak/seal advisory line set and the forced active-phase recovery-advisory string | registry persistence, phase mutation, transcript reading |
| `parser_introspection.py` | argparse parser introspection: subcommand-map extraction and per-action display-name/value-shape projections used to render the registry CLI doc | parser construction, CLI-doc orchestration |
| `content_files.py` | speak content-file readers: required-file load (rejecting missing/blank) and optional full-body load, returning trailing-newline-trimmed text | speak-command orchestration, registry persistence, rendering |
| `restore_inputs.py` | restore-input readers: validate/parse the restore event-index argument and locate a deep-copied historical collab entry by id within a pre-restore registry snapshot | restore-command orchestration, registry persistence, revision-event writing |
| `init_inputs.py` | init-command input reader: parse the raw `init` argv token stream into a validated `(title, agent id, reviewer, open-requested, work-repo)` tuple, rejecting duplicate/unknown flags and missing flag values; owns the sole-use role-key pattern and aggregates lower-tier leaves (errors, normalizers) | init-command orchestration, registry persistence, phase mutation, any write path |
| `query_commands.py` | read-only CLI query/projection command handlers: load and project a single read view (registry path, role roster rows, reviewer/handoff state, timestamps, summary role), print it, and return an exit code; aggregates lower-tier domain leaves (roles, participants, handoff_shape, registry_io, normalizers, transcript_readers) | registry persistence, phase mutation, any write path |
| `inspection_commands.py` | read-only inspection/report command handlers: list collabs, project the revision-event log, render a single-entry status view, compute drift, and audit closed collabs — load and project a multi-entry or transcript-derived read view, print it, and return an exit code; aggregates lower-tier domain leaves (registry_io, registry_state, registry_constants, normalizers, transcript_readers, participants, seal_verification, contribution_store, diff, execution, effort) | registry persistence, phase mutation, any write path |
| `post_execution.py` | post-execution lifecycle projections: given an entry and its assigned roles, compute close-eligibility after execution and the next-line guidance string after execution - read-only projections over reviewer verification and seal state, injected into `execution.py` as callbacks; aggregates lower-tier leaves (dispatch_forms, participants, seal_verification, speak_state) | registry persistence, phase mutation, any write path |
| `execution.py` | execution checks, run-plan support, write-scope enforcement, execution state recording | seal |
| `contribution_store.py` | contribution-store path and shape helpers | registry state, rendering, write path |
| `contribution_validation.py` | speak-time contribution gates, moderator contribution normalization | rendering, write path |
| `diff.py` | read-only collab drift comparison | registry writes, rendering, state mutation |
| `registry_validation.py` | schema validation | advisory math, write path |
| `release.py` | tag command behavior: dry-run plans, confirmation gate, clean-worktree checks, annotated-tag creation, and optional push | registry mutation, transcript rendering, collab lifecycle close behavior |
| `effort.py` | advisory math | schema validation, write path |
| `transcript_render.py` | managed rendering: header, TOC, all `<details>` blocks, contribution blocks, effort-override banners | registry state, phase lifecycle, write-path dispatch, CLI entry-point logic |
| `seal_verification.py` | compatibility exports for the split verification boundary; exports module-owned public functions/constants from the concrete logic/render leaves for tests and out-of-tree callers | domain ownership, registry persistence, phase lifecycle, CLI dispatch |
| `seal_verification_logic.py` | seal state readers, completion and participant-verification state, stale-seal invalidation, content-integrity and git-state gates, verdict construction and validation, chartered-deliverables coverage, and verification restart | participant-verify rendering, assessment/seal rendering, verdict/seal write entry points, registry persistence, CLI dispatch |
| `seal_verification_render.py` | participant-verify rendering, assessment/seal rendering, reviewer findings, summary/history rendering, and the write entry functions (`participant_verify_render`, `seal_write`, `record_verdict`) that call the logic module explicitly | stale-seal trigger decisions, participant-verification state ownership, verdict validation, content-integrity policy, phase lifecycle, participant roster management |

### Current state

`registry.py` is thin: package bootstrap, lazy compatibility exports, and executable delegation only. `registry_core.py` is the compatibility core and keeps facade configuration, the participant-verification render facade, the thin `validate_registry` wrapper, and the narrow orchestration wrappers (`record_execution`, `advance_phase`). Command bodies, parser definitions, dispatch tables, commit primitives, managed rendering, seal logic, and validation live in their owning modules listed above. Any new command handler lands in an owning leaf or a new cohesive leaf, never in `registry.py`.

### Boundary decisions

**Seal verification (split boundary):** `seal_verification_logic.py` owns verification state, stale-seal triggers, content-integrity gates, verdict construction, and chartered-deliverables coverage. `seal_verification_render.py` owns participant-verify/assessment/seal rendering, summary/history rendering, reviewer-findings blocks, and the write entry functions (`participant_verify_render`, `seal_write`, `record_verdict`) that call the logic module explicitly. `seal_verification.py` is a compatibility facade only; engine leaves import the concrete split modules directly.

**`transcript_render.py` (kept whole — managed-rendering boundary):** Header scaffolding, TOC management, and all `<details>` block construction share the `rendered_collapsible_block` primitive and the single-owner invariant: no caller constructs a `<details>` block outside this module. Splitting prematurely would compromise that invariant. If the module later warrants division, the documented split boundary is: `header_render.py` (header, TOC, `insert_toc_entry`) and `contribution_render.py` (contribution/collapsible-block rendering, excerpt/full-body handling, effort-override banners).

### Boundary maintenance gates

Every boundary move must satisfy all three gates before merging:

**[P1-render]** Byte-identical render gate: any item touching managed rendering (participants table, TOC, header, `<details>` scaffolding) must run the rendering helper before and after against a fixed fixture transcript and assert a zero-byte diff. Prose "behavior-equivalent" review does not satisfy this gate. Rationale: one whitespace byte of render drift silently breaks every route asserting managed-section bytes (Invariant #1).

**[P2-seal]** Paired staleness-test gate: each stale-seal trigger relocated during a seal/verification extraction must ship a shell test asserting the trigger still invalidates the seal after the move. Rationale: a seal that "appears valid but covers different evidence" is a silent failure; this gate makes it loud.

**[V-shape]** Per-item guardrail packet: source cluster, destination module, public imports retained by `registry.py`, byte-identical render assertions where [P1-render] applies, and write-path freeze confirmation.

Commit discipline: each extraction item lands as its own atomically-scoped, accurately-titled commit. Bundling a design move with behavioral assertions in one commit mislabels the record; git history is the canonical record of past outcomes.
