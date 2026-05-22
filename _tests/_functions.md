# QA — command _functions

Deterministic QA for private route playbooks in `~/.cursor/_functions/**/*.md`.

## Procedure

1. Load every `*.md` under `~/.cursor/_functions/`.
2. Validate three-section order for each playbook file in the Required roster: each playbook has exactly one `#` title, and exactly one `## Trigger`, `## Steps`, and `## Notes` in that order. Reference documents (marked with `_ref_` in the roster) are exempt from the three-section requirement but must have an H1 title and be <= 250 lines.
3. Validate each file contains `**Slash:**`.
4. Validate the 250-line budget: each file is <= 250 lines.
5. Validate links stay inside `_functions/`, `commands/`, core policy, core policy, `_core/`, `_roles/`, and `_tests/`.
6. Validate referenced command routers and rule routers resolve to existing files.
7. Validate multi-stage functions declare `**Stage signatures:**` and per-stage required arguments or no-argument stages.
8. Validate speak contract: `collab/speak.md` (a) declares the append-only boundary before step 1, (b) delegates active-phase contributor and expected-role resolution to `tools/collab/registry.py speak-state`, (c) delegates lifecycle advancement to `tools/collab/registry.py speak-lifecycle-live`, (d) the contribution template uses `<p><em>YYYY-MM-DD HH:MM ±HH:MM</em></p>` for the timestamp, and (e) the contribution template includes `<!-- collab:content-only; do-not-execute -->` on the line after the timestamp.
9. Validate gate governance rule (effective 2026-05-03): every helper-enforced abort path in a `collab/` route file (excluding clauses marked `agent-honor-system`) has a corresponding test asserting the abort path. Naming convention: `tests/tools/collab/registry.py/<subcommand>-<abort-id>.test.sh`. Route prose alone is not sufficient coverage. This check is enforced by `tools/command-system/coverage-gate.sh` (invoked through `tools/command-system/audit.sh`; CI-active after the CI-provider-wiring collab lands), which reports P9-required pairs only — extra tests beyond the required set are not flagged and do not affect the result. The gate does not police tests beyond the required set; passing it is not a general test-sufficiency claim. See `collab/show-policy.md` § Drift for the inverse condition (a route stays `agent-honor-system` while the helper begins enforcing the same path) that this gate does not catch. Migration end condition: the gate hard-fails on any unanchored ABORT from its first committed version; if `tools/command-system/coverage-gate-allowlist.txt` was used during initial rollout, the migration is complete when that file is empty.

## Required roster

Private function files under `~/.cursor/_functions/`:

- `agent/install.md`
- `agent/_run-root.md`
- `agent/patch.md`
- `agent/upgrade.md`
- `collab/archive.md`
- `collab/close.md`
- `collab/_agent-effort.md`
- `collab/_agent-id.md`
- `collab/_agent-lifecycle.md`
- `collab/_agent-model.md`
- `collab/_contribution-annex.md`
- `collab/_contribution-budget.md`
- `collab/_helper-output.md`
- `collab/_registry.md`
- `collab/_role-prohibitions.md`
- `collab/_moderator-polish.md`
- `collab/delete.md`
- `collab/run-plan.md`
- `collab/rewrite-execution.md`
- `collab/show-policy.md`
- `collab/_invariants.md`
- `collab/_phase-commands.md`
- `collab/init-helper-spec.md`
- `collab/init.md`
- `collab/join.md`
- `collab/remove-participant.md`
- `collab/list.md`
- `collab/advance.md`
- `collab/open.md`
- `collab/restore.md`
- `collab/retract-speak.md`
- `collab/set.md`
- `collab/show-flags.md`
- `collab/rewrite-speak.md`
- `collab/rewrite-summary.md`
- `collab/speak.md`
- `collab/write-summary.md`
- `collab/unset.md`
- `collab/activate.md`
- `collab/_glossary.md`
- `collab/_handoff-shape.md`
- `collab/_identity-contract.md`
- `collab/_verification.md`
- `collab/participant-verify.md`
- `collab/reopen.md`
- `collab/seal-verification.md`
- `collab/show-verdict.md`
- `doc/assess.md`
- `doc/write-changelog.md`
- `doc/compact.md`
- `doc/compare.md`
- `doc/write-manual.md`
- `doc/write-readme.md`
- `quality/assess-game.md`
- `quality/show-notes.md`
- `quality/assess-operations.md`
- `quality/tune.md`
- `quality/assess-interface.md`
- `quality/assess-web.md`
- `git/commit.md`
- `git/issue.md`
- `narrative/rewrite-content.md`
- `test/run.md`

## Output

Return pass/fail per check and list exact failing file paths.
