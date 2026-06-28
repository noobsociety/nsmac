# QA — command tests

Deterministic QA for harness docs in `~/.cursor/tests/specs/*.md`.

## Procedure

1. Load every `*.md` under `~/.cursor/tests/specs/`.
2. Validate each top-level directory under `~/.cursor/` has one same-name harness file in `~/.cursor/tests/specs/`.
3. Validate every harness filename maps to either a top-level `~/.cursor/` directory or an explicit non-`~/.cursor` projection harness.
4. Validate each harness file has one H1 and is <= 250 lines.
5. Validate no harness file points outside `~/.cursor/` or repository-level authorities.

## Required roster

Harness files under `~/.cursor/tests/specs/`:

- `commands.md`
- `core.md`
- `roles.md`
- `generated.md`
- `settings.md`
- `templates.md`
- `tests.md`

**Note — intentionally internal harness specs:** `generated.md`, `templates.md`, and `tests.md` are not exposed as `(test <target>)` routing targets. They are internal harness specifications swept by `./tests/run.sh`'s Markdown harness sweep, not dispatched through the `(test)` command.

## Principle

Add a test only when a source behavior requires executable proof; prefer shell-layer coverage over Markdown-harness duplication. The `agent-honor-system` boundary is a known limit of this criterion, not a defect.

## Suite size

`tests/run.sh` reports the live test count and elapsed seconds at execution time. Keep source behavior coverage intact; do not encode old run snapshots or quota plans in this spec.

## Layer ownership

`tests/*.test.sh` owns shell-executable CI contract validation; `tests/specs/*.md` owns agent-facing policy for the `(test)` command surface.

`platform/tooling/audit.sh` is the shell-layer owning gate for adapter routing, `commands/commands.md` discovery, and runtime ignore rules; no Markdown harness is required for these behaviors.

`tests/run.sh` is the single entry point for the full test suite and is owned by three runtimes:

- **GitHub Actions** — external runnable owner; the workflow calls `tests/run.sh` on push and pull request to `main`.
- **Local pre-commit and pre-push hooks** — installed by `platform/tooling/install-git-hooks.sh`; both hooks invoke `./tests/run.sh`.
- **Local manual invocation** — direct shell call; no harness or installer required.

`platform/tooling/audit.sh` admits `.github/**` as tracked source. This boundary covers workflow files, CODEOWNERS, dependabot config, issue templates, and PR templates — not workflow files alone.

Neither layer may be reduced without updating this statement to name the resulting ownership per layer.

**Test removal criteria:** Before any test file under `tests/` is removed, its inventory row must satisfy all of:

- `CONTRACT` names a specific surface (not a category label)
- `OWNER: central-checker` and the central checker test exercises that same surface
- `TYPE` ∈ {`structure`, `prose-duplicate`}
- For golden-file rows additionally: replacement checks land in the same batch, including a stable generate-and-compare check confirming the committed artifact does not drift from generator output

**Technical-writer sign-off gate:** `CONTRACT` must name a specific surface for every deletion row before the technical-writer role approves. Category labels such as "golden file" or "doc contract" are not acceptable `CONTRACT` values.

## Removed test inventory

| Removed test | CONTRACT | OWNER | TYPE |
| --- | --- | --- | --- |
| `budget-exempt-action-plan-checklist.test.sh` (removed; consolidated) | `commands/collab/reference/contribution-budget.md` `action-plan-checklist` exempt class accepts oversized checklist-only Action Plan contributions and rejects oversized non-exempt prose | central-checker: `tests/commands/collab/registry.py/contribution-budget-exempt-classes.test.sh` | `structure` |
| `budget-exempt-conclusion-ratification.test.sh` (removed; consolidated) | `commands/collab/reference/contribution-budget.md` `conclusion-ratification` exempt class accepts oversized ratification-only Conclusion contributions and rejects oversized non-exempt prose | central-checker: `tests/commands/collab/registry.py/contribution-budget-exempt-classes.test.sh` | `structure` |
| `budget-exempt-effort-override-line.test.sh` (removed; consolidated) | `commands/collab/reference/contribution-budget.md` `effort-override-line` exempt class accepts at-limit prose with an override line and rejects oversized non-exempt prose after stripping the override line | central-checker: `tests/commands/collab/registry.py/contribution-budget-exempt-classes.test.sh` | `structure` |
| `budget-exempt-moderator-verbatim.test.sh` (removed; consolidated) | `commands/collab/reference/contribution-budget.md` `moderator-verbatim` exempt class accepts oversized moderator-role content and rejects oversized non-moderator content | central-checker: `tests/commands/collab/registry.py/contribution-budget-exempt-classes.test.sh` | `structure` |
| `execute-spawn-returned-path.test.sh` (removed; consolidated) | `commands/collab/run-plan/index.md` parent-owned subagent integration rejects returned paths outside the assigned `execute-spawn --scope` | central-checker: `tests/commands/collab/registry.py/handoff-structured-state.test.sh` | `structure` |
| `modules/digests.test.sh` (removed; consolidated) | `commands/collab/engine/digests.py` full-body block stripping, execution signature, touched-path aggregation, active execution entry shape, and content digest behavior | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `modules/git-repo.test.sh` (removed; consolidated) | `commands/collab/engine/git_repo.py` work-tree resolution, commit provenance, staged/unstaged/deleted path state, `workRepo` resolution, and recordable touched-path checks | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `modules/handoff-shape.test.sh` (removed; consolidated) | `commands/collab/engine/handoff_shape.py` write-scope validation, validation-command normalization, effort-override hiding, Handoff content parsing, and Handoff state accessors | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `modules/normalizers.test.sh` (removed; consolidated) | `commands/collab/engine/normalizers.py` slug/title/date formatting, agent-id normalization, scope matching, touched-path normalization, restore-target validation, and timestamp formatting | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `modules/participants.test.sh` (removed; consolidated) | `commands/collab/engine/participants.py` reviewer state, participant insertion, turn-order calculation, optional reviewer admission, caller-role guards, and caller-declined identity metrics | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `modules/phase-lifecycle.test.sh` (removed; consolidated) | `commands/collab/engine/phase_lifecycle.py` phase transitions, transition notices, discussion turn notices, lifecycle status notices, and lifecycle diagnostic output | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `modules/registry-constants.test.sh` (removed; consolidated) | `commands/collab/engine/registry_constants.py` phase ordering, full-body summary line, shell/glob safety patterns, moderator-only action set, status/terminal/sub-state vocabularies, restore targets, and deleted-path sentinels | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `modules/registry-io.test.sh` (removed; consolidated) | `commands/collab/engine/registry_io.py` validator configuration, registry save/load normalization, collab resolution, revision event writing, semantic-change detection, bootstrap loading, lock creation, and invalid JSON aborts | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `modules/seal-verification-verdict-companion.test.sh` (removed; consolidated) | `commands/collab/engine/seal_verification.py` seal-verdict companion non-authority, digest binding, mismatch detection, missing-companion status, and missing-seal abort | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `registry.py/catalog-synced-clean.test.sh` (removed; consolidated) | `commands/commands.md` and `generated/command-reference.md` stay generated-clean and contain no retired `(collab synthesize)` dispatch entries | central-checker: `platform/tooling/audit.sh` | `structure` |
| `registry.py/no-raw-plane-residue.test.sh` (removed; consolidated) | `commands/collab/engine` and `registry.py --help` expose no retired raw-transcript migration banner, helper command, or migration path symbols | central-checker: `platform/tooling/audit.sh` | `structure` |
| `registry.py/no-sy-dp-prose-live-surfaces.test.sh` (removed; consolidated) | path names commands/collab/reference/synthesizers/ and commands/collab/reference/projectors/ stay absent, and `git grep` over `commands/` plus `platform/standards/` excluding `commands/collab/engine/`, `records/`, and `commands/collab/reference/roles/` finds no retired `Synthesizer` role identity prose | central-checker: `platform/tooling/audit.sh` | `structure` |
| `registry.py/no-synthesis-cli-surface.test.sh` (removed; consolidated) | `registry.py --help`, invalid-command handling, and `generated/registry-cli.md` expose no retired synthesis/projection helper commands | central-checker: `platform/tooling/audit.sh` | `structure` |
| `registry.py/no-synthesis-implementation-residue.test.sh` (removed; consolidated) | `git ls-files commands/collab/engine/synthesis.py` stays empty; path names tests/commands/collab/registry.py/synthesize-*.test.sh, tests/commands/collab/aggregate-transcript.test.sh, and tests/commands/collab/modules/transcript-render-projection-store.test.sh stay absent; `commands/collab/engine/*.py` contains no `contribution_store_digest`, `projection_source_digest`, or `projection_store_records`; and `commands.collab.engine.transcript_render` exposes `excerpt_source`, `stance_for_content`, and `is_hidden_metadata_line` without the retired `projection_*` helper names | central-checker: `platform/tooling/audit.sh` | `structure` |
| `registry.py/no-synthesis-vocab-live-surfaces.test.sh` (removed; consolidated) | `commands/collab/summarize/index.md` omits `synthesis artifacts`; `commands/collab/show-policy/index.md` omits `Projector metadata is intentionally absent`; `commands/collab/reference/role-prohibitions.md` omits the `## Deterministic Projector (dp)` section; `commands/collab/init/index.md` and `commands/collab/open/index.md` omit `(collab aggregate)` and `records/*-raw.md`; `git grep` over `commands/` plus `platform/standards/` excluding `commands/collab/engine/` and `records/` finds no `projection-mode` or `per-piece`; and `commands/collab/engine/*.py` contains no `projection_*` or `is_projection_*` render symbols | central-checker: `platform/tooling/audit.sh` | `structure` |
| `registry.py/registry-cli-doc-stale.test.sh` (removed; consolidated) | `generated/registry-cli.md` matches `commands/collab/engine/registry.py registry-cli-doc` output | central-checker: `platform/tooling/audit.sh` | `structure` |
| `registry.py/rewrite-execution-registry-target.test.sh` (removed; consolidated) | `commands/collab/rewrite-execution/index.md` retains `rewrite-execution-registry-target` abort anchor and `registry target unavailable` abort text | central-checker: `tests/commands/collab/route-doc-contracts.test.sh` | `prose-duplicate` |
| `registry.py/rewrite-speak-role-scoped-not-turn-gated.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py` `render_re_speak` contains contribution-scope guards without speak-state turn-gating tokens, and `commands/collab/rewrite-speak/index.md` retains the explicit no-turn-gating rule | central-checker: `tests/commands/collab/registry.py/speak-guards.test.sh` | `structure` |
| `registry.py/role-file-readability.test.sh` (removed; consolidated) | `commands/collab/engine/registry_validation.py` `validate_registry` rejects participants whose role source file is unreadable and reports `roles/ghost.json` | central-checker: `tests/commands/collab/modules.test.sh` | `structure` |
| `registry.py/run-plan-step8-doc.test.sh` (removed; consolidated) | `commands/collab/run-plan/index.md` Step 8 permits rerun when unchecked assigned items exist and documents execution-helper replacement semantics | central-checker: `tests/commands/collab/route-doc-contracts.test.sh` | `prose-duplicate` |
| `registry.py/seal-stale-execution-rewrite.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py execution` marks an existing verification seal stale when participant execution is rewritten | central-checker: `tests/commands/collab/registry.py/seal-stale-invalidation.test.sh` | `structure` |
| `registry.py/seal-stale-full-body.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-state` marks an existing verification seal stale when managed full-body transcript bytes change | central-checker: `tests/commands/collab/registry.py/seal-stale-invalidation.test.sh` | `structure` |
| `registry.py/seal-stale-out-of-scope-patch.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py out-of-scope-patch` marks an existing verification seal stale when a participant touches a path outside declared writeScope | central-checker: `tests/commands/collab/registry.py/seal-stale-invalidation.test.sh` | `structure` |
| `registry.py/seal-stale-transcript-repair.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py transcript-repair --touch-execution-evidence` marks an existing verification seal stale | central-checker: `tests/commands/collab/registry.py/seal-stale-invalidation.test.sh` | `structure` |
| `registry.py/seal-verification-cap-exceeded.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-render` rejects a reviewer seal without `--cap-exit` when `verification.rounds` is at `verification.cap`, then accepts a registered cap-exit without applying verdict work | central-checker: `tests/commands/collab/registry.py/verification-assessment-cap-exit.test.sh` | `structure` |
| `registry.py/seal-verification-invalid-cap-exit.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-render` rejects invalid `--cap-exit` values before rendering a verification seal | central-checker: `tests/commands/collab/registry.py/seal-verification-guards.test.sh` | `structure` |
| `registry.py/seal-verification-no-reviewer.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-render` rejects Completion records that have no active reviewer role | central-checker: `tests/commands/collab/registry.py/seal-verification-guards.test.sh` | `structure` |
| `registry.py/seal-verification-phase-not-completion.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-state` rejects verification access before the Completion phase | central-checker: `tests/commands/collab/registry.py/seal-verification-guards.test.sh` | `structure` |
| `registry.py/seal-verification-record-closed.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-state` rejects records already closed by a successful verification seal outcome | central-checker: `tests/commands/collab/registry.py/seal-verification-guards.test.sh` | `structure` |
| `registry.py/seal-verification-record-unreadable.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-state` rejects missing project-marker and unreadable registry state before verification access | central-checker: `tests/commands/collab/registry.py/seal-verification-guards.test.sh` | `structure` |
| `registry.py/seal-verification-substate-not-verification.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-render` rejects Completion records whose active sub-state is still `execution` | central-checker: `tests/commands/collab/registry.py/seal-verification-guards.test.sh` | `structure` |
| `registry.py/seal-verification-uncommitted-paths.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-render` rejects staged, unstaged, and working-tree-only execution `touchedPaths` with `SEAL-GIT-STATE`, while accepting committed present paths, committed deletions, and declared `workRepo` committed paths | central-checker: `tests/commands/collab/registry.py/seal-render-git-state.test.sh` | `structure` |
| `registry.py/seal-verification-wrong-role.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-render` rejects non-reviewer seal authors and reports the current role plus expected reviewer role | central-checker: `tests/commands/collab/registry.py/verification-seal-flow.test.sh` | `structure` |
| `registry.py/seal-verification-zero-round-no-record.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py seal-render` rejects zero-round first seal attempts without writing seal, verdict, terminal-mode, workflow-model, or sealed transcript state | central-checker: `tests/commands/collab/registry.py/seal-verification-guards.test.sh` | `structure` |
| `registry.py/show-verdict-output.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py show-verdict` emits closed-collab target, phase, verification sub-state, verdict, seal metadata, and rejects missing registry targets | central-checker: `tests/commands/collab/seal-verdict.test.sh` | `structure` |
| `registry.py/summarize-active-phase-missing.test.sh` (removed; consolidated) | `commands/collab/summarize/index.md` retains the `summarize-active-phase-missing` abort anchor | central-checker: `tests/commands/collab/route-doc-contracts.test.sh` | `prose-duplicate` |
| `registry.py/summarize-no-contributions.test.sh` (removed; consolidated) | `commands/collab/summarize/index.md` retains the `summarize-no-contributions` abort anchor | central-checker: `tests/commands/collab/route-doc-contracts.test.sh` | `prose-duplicate` |
| `registry.py/summarize-record-unreadable.test.sh` (removed; consolidated) | `commands/collab/summarize/index.md` retains the `summarize-record-unreadable` abort anchor | central-checker: `tests/commands/collab/route-doc-contracts.test.sh` | `prose-duplicate` |
| `registry.py/summarize-registry-target-unavailable.test.sh` (removed; consolidated) | `commands/collab/summarize/index.md` retains the `summarize-registry-target-unavailable` abort anchor | central-checker: `tests/commands/collab/route-doc-contracts.test.sh` | `prose-duplicate` |
| `registry.py/speak-render-stale-revision.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py speak-render` rejects stale observed registry revisions | central-checker: `tests/commands/collab/registry.py/speak-guards.test.sh` | `structure` |
| `registry.py/speak-state-pending-reviewer.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py speak-state` rejects contributions while the configured reviewer role is still pending | central-checker: `tests/commands/collab/registry.py/speak-guards.test.sh` | `structure` |
| `registry.py/target-spec-template-runtime-exemption.test.sh` (removed; consolidated) | retired target-format transcript templates remain absent and `commands/collab/reference/anchor-convention.md` cites `commands/collab/engine/transcript_render.py` as emitter source | central-checker: `platform/tooling/audit.sh` | `structure` |
| `registry.py/verification-round-call-sites.test.sh` (removed; consolidated) | `commands/collab/engine/registry.py` records paired verification rounds only in `participant_verify_render`, never in `render_seal` | central-checker: `platform/tooling/audit.sh` | `structure` |

## Output

Return pass/fail per check and list exact failing file paths.
