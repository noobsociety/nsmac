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

Weekly-review measurement (W25 window `b8dead7..4cf5fe5`, through 2026-06-21): **110** test scripts (`*.test.sh`) tracked in-window at `4cf5fe5`, against an advisory budget of **<=80**; the W25 review run completed in **181s**. Next weekly target: reduce the suite to **<=100** tracked test scripts by the next weekly review while preserving shell-layer coverage for every source behavior that still requires executable proof.

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
| `tests/commands/collab/registry.py/budget-exempt-action-plan-checklist.test.sh` | `commands/collab/reference/contribution-budget.md` `action-plan-checklist` exempt class accepts oversized checklist-only Action Plan contributions and rejects oversized non-exempt prose | `central-checker: tests/commands/collab/registry.py/contribution-budget-exempt-classes.test.sh` | `structure` |
| `tests/commands/collab/registry.py/budget-exempt-conclusion-ratification.test.sh` | `commands/collab/reference/contribution-budget.md` `conclusion-ratification` exempt class accepts oversized ratification-only Conclusion contributions and rejects oversized non-exempt prose | `central-checker: tests/commands/collab/registry.py/contribution-budget-exempt-classes.test.sh` | `structure` |
| `tests/commands/collab/registry.py/budget-exempt-effort-override-line.test.sh` | `commands/collab/reference/contribution-budget.md` `effort-override-line` exempt class accepts at-limit prose with an override line and rejects oversized non-exempt prose after stripping the override line | `central-checker: tests/commands/collab/registry.py/contribution-budget-exempt-classes.test.sh` | `structure` |
| `tests/commands/collab/registry.py/budget-exempt-moderator-verbatim.test.sh` | `commands/collab/reference/contribution-budget.md` `moderator-verbatim` exempt class accepts oversized moderator-role content and rejects oversized non-moderator content | `central-checker: tests/commands/collab/registry.py/contribution-budget-exempt-classes.test.sh` | `structure` |
| `tests/commands/collab/registry.py/execute-spawn-returned-path.test.sh` | `commands/collab/run-plan/index.md` parent-owned subagent integration rejects returned paths outside the assigned `execute-spawn --scope` | `central-checker: tests/commands/collab/registry.py/handoff-structured-state.test.sh` | `structure` |

## Output

Return pass/fail per check and list exact failing file paths.
