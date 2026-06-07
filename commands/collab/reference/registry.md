# /collab registry

Reference document for the resolved collab `registry.json` schema and field ownership used by all collab routes.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab registry schema, registry fields, collab registry reference, activeCollabId, execution field

## Steps

1. Read this document when resolving registry field semantics, ownership rules, or the shared helper contract.
2. Do not mutate registry state from this documentation-only reference.

## Notes

- **Registry contract:** The default registry is resolved from `.collab.json` to `$HOME/.collabs/<projectId>/registry.json`; `--registry` bypasses that resolver. The registry is the authoritative source for durable collab metadata: target selection, lifecycle phase, status, participants, turn order, reviewer configuration, structured Handoff state, execution metadata, verification state, seals, and verdicts. Markdown transcripts under `records/*.md` in the same user-scope collab state root are the human ledger and are parsed only by helper-owned transcript readers for transcript-authored evidence: contribution order, Action Plan checklist assignments, chartered deliverables, full-body drift signatures, and verification inputs.

- **Lock lifecycle:** Registry and transcript mutations serialize through a persistent `registry.json.lock` file beside `registry.json` in the user-scope collab state root. Normal writes do not delete this file; removing an `fcntl` lock path can split waiting processes across different inodes. An idle lock file is valid state; validation refreshes an aged idle lock marker in place rather than deleting it. Validation reports an aged lock only when another process still actively holds it, with guidance to confirm whether the command is stuck before terminating it.

- **Top-level fields:**

  | Field | Type | Description |
  | --- | --- | --- |
  | `activeCollabId` | string or null | `id` of the currently selected collab. `null` when no collab is active. Owned by `activate`; cleared by `close`, `archive`, or completion auto-close when the selected collab is no longer active. |

- **Per-collab entry fields:**

  | Field | Type | Description |
  | --- | --- | --- |
  | `id` | string | Immutable internal key. Format: `YYYY-MM-DD-<slug>`. Set at `init`; never changed. |
  | `sequence` | integer | Stable numeric selector shown by `/collab list` as `#N`. Assigned at `init` from insertion order and never reused after hard delete. |
  | `slug` | string | User-facing handle. Format: lowercased, hyphen-separated words. Used in commands instead of file paths. |
  | `title` | string | Human-readable name from `init`. |
  | `description` | string | Brief description from `init`. |
  | `workRepo` | string or absent | Resolved absolute path of the project git tree. Bound at init via `--work-repo <path>` or recovered via `/collab set work-repo <path>`; persisted as an absolute path and scoped to all git-ops (touched-path verification, git-state checks, seal). When the resolved path equals the framework ROOT (`~/.cursor`) but `projectId` does not match the dotcursor project, the helper emits a loud failure rather than silently operating on the wrong repo. When absent, resolution falls back to the framework ROOT, which is only valid when the collab is for the dotcursor project itself. See [workRepo remediation index](workRepo-remediation-index.md) for the R1–R7 remediation items that shaped this field's semantics. |
  | `createdAt` | string | ISO-8601 creation timestamp set by `init` for records created after the terminal selector contract. Records without `createdAt` predate this contract and are grandfathered without rewrite. |
  | `terminal` | string | Workflow-model terminal selector: `seal|issue`. Set by `init` from `--terminal <seal|issue>` and defaulted to `seal` for new records. Records without `terminal` predate this contract and are grandfathered without rewrite. |
  | `status` | string | `open` \| `closed` \| `archived`. |
  | `activePhase` | string | Current phase: `Audit` \| `Discussion` \| `Conclusion` \| `Action Plan` \| `Handoff` \| `Completion`. `Completion` is further divided into `Completion.execution` (assigned roles run their Action Plan items) and `Completion.verification` (reviewer seals via `/collab seal verification`) for reviewer-backed collabs. |
  | `moderatorRole` | string | Key of the moderator participant. |
  | `participants` | `{ role: string, agentId: string }[]` | Ordered list of registered participants. Each entry records the role key and the joining agent's at-join `agentId` per [agent-id.md](agent-id.md). |
  | `turnOrder` | string[] | Ordered cycle of speaking keys enforced by `speak`. When empty, `speak` falls back to `participants` order. |
  | `reviewerRole` | string | Optional reviewer key for collab-level judgment passes. May be written before the role is listed in `participants`; while pending, `speak-state` aborts before turn-order checks. |
  | `reviewerMode` | string | Optional reviewer behavior mode. Initial supported value: `last-in-convergent-phases`. |
  | `reviewerOptionalPhases` | string[] | Optional phase names where the reviewer may speak without blocking the ordinary expected speaker. Defaults to `Discussion` when a reviewer is set. Mutating this field affects only the current or later active phase; it does not retroactively admit the reviewer into a phase that has already advanced. |
  | `transcriptPath` | string | Relative path to the markdown transcript inside the state root: `records/<id>.md`. |
  | `archived` | boolean | `true` after a soft delete via `archive`. |
  | `execution` | object | Keyed by role key. Each value: `{ "status": "in_progress" \| "completed" \| "failed", "date": "YYYY-MM-DD", "agentId"?: string, "validationResult"?: string, "validationScope"?: "scoped" \| "full" \| "deferred", "touchedPaths"?: string[] }`. `in_progress` is reserved for true pre-work async dispatch or necessary retry trace; default successful execution records are `completed` with validation scope and touched paths. When structured Handoff state exists for the role, `touchedPaths` must be inside `handoff.roles.<role>.writeScope`. For reviewer-backed collabs, completing all `execution.<role>` entries does not trigger auto-close; a current non-stale `verificationSeal` is also required. |
  | `completion.subState` | string | `"execution"` \| `"verification"`. Present when the `Completion` phase is active for a reviewer-backed collab. Set to `"verification"` after all assigned `execution.<role>` entries are `completed`; transitions back to `"execution"` after a reopen-handoff or reopen-action-plan cap exit. Absent for non-reviewer-backed collabs. |
  | `verification.subState` | string | `"participant"` \| `"seal"` \| `"assessment"`. Active within `Completion.verification` for reviewer-backed collabs. Set to `"participant"` when participant verification begins (if configured); transitions to `"seal"` when all assigned participant verifications complete; transitions to `"assessment"` after a successful seal. Re-enters `"assessment"` when the seal becomes stale or a cap-exit is recorded. |
  | `verification.participantVerification` | boolean | Enables the `verification.participant` sub-state when set by init. |
  | `verification.participants[role].stage` | string | Per-role participant-verification stage. Values: `"audit"` \| `"remediation"` \| `"final-audit"` \| `"completed"` \| `"failed"`. Set and read by `/collab participant verify`. Absent when participant verification is not configured or the role has not yet begun its sequence. |
  | `verification.participants[role].attempts` | integer | Per-role participant-verification attempt count for the active `writeScope` signature. |
  | `verification.participants[role].writeScopeSignature` | string | SHA-256 signature of the role's Handoff `writeScope`; changing the signature resets the role's participant-verification attempt budget. |
  | `verification.rounds` | integer | Count of reviewer-executor paired events recorded in the current `Completion.verification` cycle. Incremented by `seal-state` when a reviewer event is paired with executor patch events. Zero at start of each verification cycle; hard seal rejection at zero. |
  | `verification.cap` | integer | Maximum allowed verification rounds before a cap-exit action is required. Set at collab init or via `/collab set verification-cap <n>`. When `verification.rounds` reaches `verification.cap`, the next seal attempt requires `--cap-exit`. |
  | `verificationSeal` | object | Written atomically by `seal-render` when `/collab seal verification` succeeds. Shape: `{ observedRevision: integer, executionEntries: object[], validationScopes: string[], touchedPaths: string[], sealedAt: ISO-8601, sealedBy: string, capExit?: string, followUp?: { restoreReason: string, evidence: object, failureCategory: string } }`. Invalidated (stale) by execution rewrites, transcript repair touching execution evidence, or out-of-scope patches. A stale or absent `verificationSeal` blocks close for reviewer-backed collabs. |
  | `verdict` | object | Written by the reviewer during `verification.assessment`. Shape: `{ outcome: "success" \| "incomplete" \| "failed", restoreTarget?: string, restoreReason?: string, evidence?: object, failureCategory?: string, nullResult?: boolean }`. `restoreTarget` and `restoreReason` are required when `outcome != success`; `restoreTarget` must be a registered phase ≤ the current lifecycle position. `evidence` contains read-only anchors (transcript ids, registry revision, committed paths, execution entry ids) only. `nullResult: true` with a one-line justification is required when no actionable cause is identifiable. On `outcome == success`, close and summary may proceed; on `incomplete` or `failed`, the helper prompts the next responsible role and exact command without auto-executing. |

- **Reviewer invariants:** When `reviewerRole` is set, it may be absent from `participants` while assignment is deferred, must not equal `moderatorRole`, and must not appear in ordinary `turnOrder` while `reviewerMode` is `last-in-convergent-phases`. `speak-state` aborts before turn-order checks while the reviewer is pending. After the reviewer role is listed in `participants`, `speak-state` computes reviewer-aware expected speakers: in `Audit` and `Conclusion`, ordinary turn-order roles speak first and the reviewer speaks last once; in phases listed by `reviewerOptionalPhases`, the reviewer is optional and admitted only at the tail of a completed ordinary round. In `Completion.verification`, the reviewer's terminal obligation is to issue `/collab seal verification` — not to run the full test suite (which is owned by the terminal execution turn). Auto-close is blocked for reviewer-backed collabs until a current non-stale `verificationSeal` exists alongside all completed `execution.<role>` entries. The terminal-reviewer contract (formerly described as owning the full-suite run) is superseded by the seal: the reviewer's role in `Completion.verification` is to judge correctness of the executed scope and seal against it.

- **Transcript status rendering:** `commands/collab/engine/registry.py render-status <target>` renders the transcript status table from registry state, including the `Reviewer` cell. Render `—` when no reviewer is set. Route playbooks should delegate status-table mirroring to this helper rather than manually owning reviewer cells.

- **Role catalog:** `commands/collab/engine/registry.py roles --roles-dir <dir>` validates role JSON files and emits stable participant rows for public role-discovery surfaces.

- **Execution boundary helpers:** `commands/collab/engine/registry.py write-guard <route> <path>...` centralizes the write boundary: routes other than `execute` may write only under `registry.json`, `registry.json.lock`, or `records/` inside the user-scope collab state root. `execution` records may include `validationResult`, `validationScope`, and `touchedPaths` so `/collab run plan` can preserve validation and blast-radius metadata.

- **Field ownership:**

  | Field | Owned by |
  | --- | --- |
  | `activeCollabId` | `activate`; cleared by `close` |
  | `status` | `close`, `open`, `archive`, `execute` auto-close |
  | `activePhase` | `next`, `prev`; `set --force` for recovery only |
  | `participants` | `join`, `kick` |
  | `turnOrder` | `set` |
  | `reviewerRole`, `reviewerMode`, `reviewerOptionalPhases` | `set`, `unset`, `init`; helper validation |
  | `createdAt` | `init` |
  | `terminal` | `init` |
  | `title`, `description` | `set` |
  | `workRepo` | `init` (via `--work-repo`), `set` |
  | `archived` | `archive` |
  | `execution.<role>` | `execute` |
  | `completion.subState` | `execute` (set to `verification` when all assigned roles complete); `seal-render` (resets on cap-exit) |
  | `verification.subState` | `execute`/`seal-state` (set to `participant` or `seal` on verification start, and repaired back to `participant` when participant verification is incomplete); `participant-verify-render` (transitions from `participant` to `seal`); `seal-render` (transitions to `assessment` after successful seal or on stale/cap-exit) |
  | `verification.rounds` | `seal-state` (via `seal-render` round accounting) |
  | `verification.cap` | `set`, `init` |
  | `verificationSeal` | `seal-render`; stale-seal trigger in `rewrite-execution`, transcript repair, scope-gate helpers |
  | `verdict` | reviewer (written during `verification.assessment`; `seal-render` validates shape) |

- **Shared helper:** `commands/collab/engine/registry.py` is the single implementation of registry read, write, and target resolution. Helper-owned transcript reader code lives in `commands/collab/engine/transcript_readers.py` and is limited to deriving state that is authored in transcript prose, including contributors, Action Plan assignments, chartered deliverables, and verification inputs. All collab routes delegate registry access to these helpers. Route specs reference the helpers by name and do not restate the resolution algorithm.

- **Decomposition follow-up:** `commands/collab/engine/transcript_readers.py` is the first extraction from the registry helper. Remaining registry-helper decomposition should proceed by bounded behavior slices with same-change tests, preserving `commands/collab/engine/registry.py` as the public CLI entry point unless a route contract explicitly moves a subcommand.

### Proposed #57: `commands/collab/engine/transcript_render.py`

#57 should extract the managed transcript rendering and transcript-display surface from `commands/collab/engine/registry.py` into `commands/collab/engine/transcript_render.py`. Baseline before the extraction: `commands/collab/engine/registry.py` is 6008 lines. Success requires either `commands/collab/engine/registry.py` at 5200 lines or fewer after #57, or a per-symbol assertion that every retained `registry.py` binding for moved surface is import-only or a dispatch wrapper with no rendering/transcript logic left behind.

Extraction sequence:

1. Move transcript read/view and next-command helpers: `transcript_view_command`, `read_transcript_for_entry`, `next_line_for_state`, `next_line_after_speak`, `next_line_after_execution`, `transcript_view`, and `transcript_repair`.
2. Move effort and contribution rendering helpers: `normalize_rendered_effort_cell`, `rendered_effort_drift_items`, `render_full_body_block`, `render_contribution_body`, `render_handoff_mirror_lines`, `render_contribution_block`, `render_speak`, `contribution_block_bounds`, and `render_re_speak`.
3. Move managed header and status renderers: `rendered_status_table`, `rendered_participants_table`, `rendered_prohibitions_block`, `rendered_reviewer_section`, `rendered_table_of_contents`, `rendered_managed_header`, `render_managed_header_text`, `render_initial_transcript`, and `render_initial_transcript_legacy`.
4. Move CLI render dispatchers that own transcript output bytes: `render_status`, `render_participants`, `role_row_command`, and `summary_role_command`.

Retained facade rule: each moved symbol remains importable from `commands.collab.engine.registry` by importing it from `commands.collab.engine.transcript_render` at the top of `registry.py`; CLI subcommand branches may remain in `registry.py` only as argument parsing and direct dispatch. If a moved command needs local state such as `DEFAULT_ROLES_DIR`, `DEFAULT_CONFIG_ROOT`, or `load_registry`, pass it as an argument rather than importing `commands.collab.engine.registry` from `transcript_render.py`.

#57 validation must include a byte-identical render fixture covering managed header, status table, participant table, Handoff mirror replacement, speak render, rewrite-speak render, transcript repair, and transcript view output before and after the extraction. The existing gates `./tests/run.sh` and `./platform/tooling/audit.sh` still apply.

#58 should use the same charter shape for seal/verification extraction: name the moved symbols, preserve `commands.collab.engine.registry` imports or dispatch wrappers, set a concrete `registry.py` line-count target from that collab's starting baseline, and pair every stale-seal trigger move with a same-change test.
