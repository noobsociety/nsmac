# QA — command tests

Deterministic QA for harness docs in `~/nsmac/tests/specs/*.md`.

## Procedure

1. Load every `*.md` under `~/nsmac/tests/specs/`.
2. Validate each top-level directory under `~/nsmac/` has one same-name harness file in `~/nsmac/tests/specs/`.
3. Validate every harness filename maps to either a top-level `~/nsmac/` directory or an explicit non-`~/nsmac` projection harness.
4. Validate each harness file has one H1 and is <= 250 lines.
5. Validate no harness file points outside `~/nsmac/` or repository-level authorities.

## Required roster

Harness files under `~/nsmac/tests/specs/`:

- `commands.md`
- `core.md`
- `roles.md`
- `generated.md`
- `settings.md`
- `templates.md`
- `tests.md`

**Note — intentionally internal harness specs:** `generated.md`, `templates.md`, and `tests.md` are not exposed as `(test <target>)` routing targets. They are internal harness specifications covered by the full suite, not dispatched through the `(test)` command.

## Principle

Add a test only when a source behavior requires executable proof; prefer shell-layer coverage over Markdown-harness duplication. The `agent-honor-system` boundary is a known limit of this criterion, not a defect.

## Suite size

`tests/run.sh` reports the live test count and elapsed seconds at execution time. Keep source behavior coverage intact; do not encode old run snapshots or quota plans in this spec.
The retained manifest is described in [`tests/suites/README.md`](../suites/README.md).

## Layer ownership

`tests/*.test.sh` owns shell-executable CI contract validation; `tests/specs/*.md` owns agent-facing policy for the `(test)` command surface.

`platform/tooling/audit.sh` is the shell-layer owning gate for adapter routing, `commands/commands.md` discovery, and runtime ignore rules; no Markdown harness is required for these behaviors.

`tests/run.sh` is the single entry point for the retained test suite.

- **GitHub Actions** — external runnable owner; the workflow calls `./tests/run.sh` on push and pull request to `main`.
- **Local pre-commit and pre-push hooks** — installed by
  `platform/tooling/install-git-hooks.sh`; both hooks invoke `./tests/run.sh`.
- **Local manual invocation** — direct shell call; no harness or installer
  required.

`platform/tooling/audit.sh` admits `.github/**` as tracked source. This boundary covers workflow files, CODEOWNERS, dependabot config, issue templates, and PR templates — not workflow files alone.

Neither layer may be reduced without updating this statement to name the resulting ownership per layer.

## Central ABORT Coverage

Some route ABORT anchors are covered by broader central tests rather than a one-file-per-anchor P9 test. The coverage gate reads this table and accepts a row only when the named checker exists.

| Anchor | Checker |
| --- | --- |
| `rewrite-execution-registry-target` | `tests/commands/collab/route-doc-contracts.test.sh` |
| `summarize-active-phase-missing` | `tests/commands/collab/route-doc-contracts.test.sh` |
| `summarize-no-contributions` | `tests/commands/collab/route-doc-contracts.test.sh` |
| `summarize-record-unreadable` | `tests/commands/collab/route-doc-contracts.test.sh` |
| `summarize-registry-target-unavailable` | `tests/commands/collab/route-doc-contracts.test.sh` |

## Output

Return pass/fail per check and list exact failing file paths.
