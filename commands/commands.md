# /commands

List public slash commands under `~/.cursor/commands/` and their private function routes; use when you need canonical invocation syntax.

Contract: [_core/command-standard.md](../_core/command-standard.md)

## Trigger

**Slash:** `/commands`
**Phrases:** `cursor commands list`, `slash commands`, `what commands in commands/`, `commands-index`

## Steps

1. Read this table when the user needs the canonical name for a playbook or the list of installed slashes.
2. Open the public command file under `CURSOR_CONFIG_ROOT/commands/` for routing behavior.
3. Open the linked private function file under `CURSOR_CONFIG_ROOT/_functions/` for full route behavior.

## Notes

Public slash files live only as `commands/<namespace>.md`. Private route functions live as `_functions/<namespace>/<route>.md` so Cursor does not expose routes as standalone slashes such as `/assess`.

Invoke routes as `/namespace route ...`; for example, `/doc assess @README.md` loads `commands/doc.md`, resolves `assess`, then executes `_functions/doc/assess.md` with the remaining input and attachments.

Operational function playbooks may depend on router rules in `../rules/{auto,shared}.mdc` and private rule files under `../_mdc/{auto,shared}/*.mdc`. `/test` may also require `~/.cursor/_tests/commands.md`, `~/.cursor/_tests/rules.md`, `~/.cursor/_tests/_functions.md`, `~/.cursor/_tests/_mdc.md`, `~/.cursor/_tests/_core.md`, `~/.cursor/_tests/_settings.md`, and `REPOSITORY.md`.

**Invocation notes by command:**

- **`/agent <install | patch | upgrade>`** — install the multi-agent scaffold (`CLAUDE.md`, `AGENTS.md`, `REPOSITORY.md`) from `~/.cursor/_templates/` into the current repo, patch `REPOSITORY.md` with repo-specific mutation protocol and ownership rules, or upgrade installed scaffold files to the current templates; `install` aborts if any scaffold file already exists (pass `--force` to enter the diff-and-confirm path instead); `patch` aborts if `REPOSITORY.md` is absent or has no `<!-- TODO(patch): ... -->` placeholders; `upgrade` compares installed files against current templates and gates any overwrite.
- **`/collab <init | join | speak | retract speak | rewrite speak | advance | restore | set | unset | list | activate | open | reopen | close | remove participant | archive | delete | write summary | rewrite summary | run plan | rewrite execution | show policy | show flags | show verdict | seal verification>`** — create, join, contribute to, retract or rewrite the last contribution, move between phases, reopen from non-success verdicts, rewrite execution records, edit or clear scoped metadata, manage active collabs, reopen/close, manage participants, soft-delete (archive) or permanently delete, write or rewrite summaries, run assigned action-plan items for a moderated collaboration record, read the gate policy, display the generated flag inventory or verdict metadata, or seal the `Completion.verification` sub-state after a reviewer pass; moderator-role contributions require human-authored text passed as `<message>` to `/collab speak` after joining with the moderator role.
  - **Retract.** `/collab retract speak` tombstones the current role's latest active-phase contribution while preserving original text for audit history.
  - **Seal.** `/collab seal verification` records the reviewer's `verificationSeal` object and triggers close or a cap-exit action (reopen-action-plan, reopen-handoff, archive); reviewer role only; zero verification rounds is a hard ABORT.
- **`/narrative rewrite content <audit | align | gate> --role <key>`** — staged narrative rewrite workflow with a required per-phase role; `align` checks project-local `*.mdc` files against `~/.cursor/rules/`; `gate` reads `validationCommands` from `.revamps/<repo>-<date>.json`.
- **`/doc write readme`** — create or update repo `README*` or `readme*` files.
- **`/doc write manual`** — create or update repo-root `MANUAL.md` from traced automation.
- **`/doc write changelog <atomic | squash>`** — `atomic` or `squash` mode keyword required.
- **`/doc assess <path>`** — Markdown path or attachment; classify and rewrite.
- **`/doc compare <path1> <path2>`** — two Markdown paths or attachments; no compact final.
- **`/doc compact <path>`** — Markdown path or attachment; preserve facts while compacting.
- **`/git commit <atomic | squash <from> <to>>`** — split working tree or squash an inclusive range.
- **`/git issue <create | implement> <goal>`** — create issue handoff or implement grounded work.
- **`/quality assess interface <image> <project>`** — screenshot UI review; attachment counts as `image`.
- **`/quality assess web <project>`** — web stack review.
- **`/quality assess game <project>`** — game engineering review.
- **`/quality assess operations <project>`** — build and operations review.
- **`/quality tune <interface | web | game | operations> ...`** — specialist pass plus cross-cutting Criteria audit.
- **`/quality show notes`** — internal route; loaded only by `/quality tune`; do not invoke directly.
- **`/test <commands | rules | _functions | _mdc | _core | _settings | repo | all>`** — run one QA harness target or all in sequence.

**Advisory surface:** The system recommends but does not enforce; callers may invoke any route at any capability or effort level at their own discretion.

**Related principal workflows:**

| Route | Source of truth | Cross-stack |
| --- | --- | --- |
| `/quality assess interface` | `image` and `project` both required; attachment counts as `image`; with attachment first token is `project` | Screenshot-only by default. |
| `/quality assess web` | `project` — checked-in web tree | On Phaser repos: non-game aspects such as host, build, shell, BFF, and DOM outside canvas. |
| `/quality assess game` | `project` — game tree | On non-Phaser repos: game slice such as loop, canvas, and assets only. |
| `/quality assess operations` | `project` — checked-in build/ops tree | Owns `tools/`, Vite output/path correctness, and CI/deploy mechanics outside web/game/interface-owned surfaces. |

**Commands catalog:**

<!-- BEGIN GENERATED:COMMANDS_ROSTER -->
_Generated by `tools/cursor/sync-commands-catalog.sh`; do not edit this block by hand._

| Slash | Signature | Public router | Private functions |
| --- | --- | --- | --- |
| `/agent` | `/agent <install \| patch \| upgrade>` | [agent](agent.md) | [_run-root](../_functions/agent/_run-root.md), [install](../_functions/agent/install.md), [patch](../_functions/agent/patch.md), [upgrade](../_functions/agent/upgrade.md) |
| `/collab` | `/collab <init \| join \| speak \| retract speak \| rewrite speak \| advance \| restore \| set \| unset \| list \| activate \| open \| reopen \| close \| remove participant \| archive \| delete \| write summary \| rewrite summary \| run plan \| rewrite execution \| participant verify \| show policy \| show flags \| show verdict \| seal verification>` | [collab](collab.md) | [_agent-effort](../_functions/collab/_agent-effort.md), [_agent-id](../_functions/collab/_agent-id.md), [_agent-lifecycle](../_functions/collab/_agent-lifecycle.md), [_agent-model](../_functions/collab/_agent-model.md), [_contribution-annex](../_functions/collab/_contribution-annex.md), [_contribution-budget](../_functions/collab/_contribution-budget.md), [_glossary](../_functions/collab/_glossary.md), [_handoff-shape](../_functions/collab/_handoff-shape.md), [_helper-output](../_functions/collab/_helper-output.md), [_honor-system-audit](../_functions/collab/_honor-system-audit.md), [_identity-contract](../_functions/collab/_identity-contract.md), [_invariants](../_functions/collab/_invariants.md), [_moderator-polish](../_functions/collab/_moderator-polish.md), [_phase-commands](../_functions/collab/_phase-commands.md), [_planned-routes](../_functions/collab/_planned-routes.md), [_registry-state](../_functions/collab/_registry-state.md), [_registry](../_functions/collab/_registry.md), [_role-prohibitions](../_functions/collab/_role-prohibitions.md), [_verification](../_functions/collab/_verification.md), [activate](../_functions/collab/activate.md), [advance](../_functions/collab/advance.md), [archive](../_functions/collab/archive.md), [close](../_functions/collab/close.md), [delete](../_functions/collab/delete.md), [init-helper-spec](../_functions/collab/init-helper-spec.md), [init](../_functions/collab/init.md), [join](../_functions/collab/join.md), [list](../_functions/collab/list.md), [open](../_functions/collab/open.md), [participant verify](../_functions/collab/participant-verify.md), [remove participant](../_functions/collab/remove-participant.md), [reopen](../_functions/collab/reopen.md), [restore](../_functions/collab/restore.md), [retract speak](../_functions/collab/retract-speak.md), [rewrite execution](../_functions/collab/rewrite-execution.md), [rewrite speak](../_functions/collab/rewrite-speak.md), [rewrite summary](../_functions/collab/rewrite-summary.md), [run plan](../_functions/collab/run-plan.md), [seal verification](../_functions/collab/seal-verification.md), [set](../_functions/collab/set.md), [show flags](../_functions/collab/show-flags.md), [show policy](../_functions/collab/show-policy.md), [show verdict](../_functions/collab/show-verdict.md), [speak](../_functions/collab/speak.md), [unset](../_functions/collab/unset.md), [write summary](../_functions/collab/write-summary.md) |
| `/doc` | `/doc <assess \| compact \| compare \| write changelog \| write manual \| write readme>` | [doc](doc.md) | [assess](../_functions/doc/assess.md), [compact](../_functions/doc/compact.md), [compare](../_functions/doc/compare.md), [write changelog](../_functions/doc/write-changelog.md), [write manual](../_functions/doc/write-manual.md), [write readme](../_functions/doc/write-readme.md) |
| `/git` | `/git <commit \| issue>` | [git](git.md) | [commit](../_functions/git/commit.md), [issue](../_functions/git/issue.md) |
| `/narrative` | `/narrative <rewrite content>` | [narrative](narrative.md) | [rewrite content](../_functions/narrative/rewrite-content.md) |
| `/quality` | `/quality <assess interface \| assess web \| assess game \| assess operations \| tune \| show notes>` | [quality](quality.md) | [assess game](../_functions/quality/assess-game.md), [assess interface](../_functions/quality/assess-interface.md), [assess operations](../_functions/quality/assess-operations.md), [assess web](../_functions/quality/assess-web.md), [show notes](../_functions/quality/show-notes.md), [tune](../_functions/quality/tune.md) |
| `/test` | `/test <commands \| rules \| _functions \| _mdc \| _core \| _roles \| _settings \| repo \| all>` | [test](test.md) | [test](../_functions/test/run.md) |

| Route | Private function |
| --- | --- |
| `(reference only — not an invocable route)` | [agent/_run-root.md](../_functions/agent/_run-root.md) |
| `/agent install` | [agent/install.md](../_functions/agent/install.md) |
| `/agent patch` | [agent/patch.md](../_functions/agent/patch.md) |
| `/agent upgrade` | [agent/upgrade.md](../_functions/agent/upgrade.md) |
| `(reference only — not an invocable route)` | [collab/_agent-effort.md](../_functions/collab/_agent-effort.md) |
| `(reference only — not an invocable route)` | [collab/_agent-id.md](../_functions/collab/_agent-id.md) |
| `(reference only — not an invocable route)` | [collab/_agent-lifecycle.md](../_functions/collab/_agent-lifecycle.md) |
| `(reference only — not an invocable route)` | [collab/_agent-model.md](../_functions/collab/_agent-model.md) |
| `(reference only — not an invocable route)` | [collab/_contribution-annex.md](../_functions/collab/_contribution-annex.md) |
| `(reference only — not an invocable route)` | [collab/_contribution-budget.md](../_functions/collab/_contribution-budget.md) |
| `(reference only — not an invocable route)` | [collab/_glossary.md](../_functions/collab/_glossary.md) |
| `(reference only — not an invocable route)` | [collab/_handoff-shape.md](../_functions/collab/_handoff-shape.md) |
| `(reference only — not an invocable route)` | [collab/_helper-output.md](../_functions/collab/_helper-output.md) |
| `(reference only — not an invocable route)` | [collab/_honor-system-audit.md](../_functions/collab/_honor-system-audit.md) |
| `(reference only — not an invocable route)` | [collab/_identity-contract.md](../_functions/collab/_identity-contract.md) |
| `(reference only — not an invocable route)` | [collab/_invariants.md](../_functions/collab/_invariants.md) |
| `(reference only — not an invocable route)` | [collab/_moderator-polish.md](../_functions/collab/_moderator-polish.md) |
| `(reference only — not an invocable route)` | [collab/_phase-commands.md](../_functions/collab/_phase-commands.md) |
| `(reference only — not an invocable route)` | [collab/_planned-routes.md](../_functions/collab/_planned-routes.md) |
| `(reference only — not an invocable route)` | [collab/_registry-state.md](../_functions/collab/_registry-state.md) |
| `(reference only — not an invocable route)` | [collab/_registry.md](../_functions/collab/_registry.md) |
| `(reference only — not an invocable route)` | [collab/_role-prohibitions.md](../_functions/collab/_role-prohibitions.md) |
| `(reference only — not an invocable route)` | [collab/_verification.md](../_functions/collab/_verification.md) |
| `/collab activate` | [collab/activate.md](../_functions/collab/activate.md) |
| `/collab advance` | [collab/advance.md](../_functions/collab/advance.md) |
| `/collab archive` | [collab/archive.md](../_functions/collab/archive.md) |
| `/collab close` | [collab/close.md](../_functions/collab/close.md) |
| `/collab delete` | [collab/delete.md](../_functions/collab/delete.md) |
| `(reference only — not an invocable route)` | [collab/init-helper-spec.md](../_functions/collab/init-helper-spec.md) |
| `/collab init` | [collab/init.md](../_functions/collab/init.md) |
| `/collab join` | [collab/join.md](../_functions/collab/join.md) |
| `/collab list` | [collab/list.md](../_functions/collab/list.md) |
| `/collab open` | [collab/open.md](../_functions/collab/open.md) |
| `/collab participant verify` | [collab/participant-verify.md](../_functions/collab/participant-verify.md) |
| `/collab remove participant` | [collab/remove-participant.md](../_functions/collab/remove-participant.md) |
| `/collab reopen` | [collab/reopen.md](../_functions/collab/reopen.md) |
| `/collab restore` | [collab/restore.md](../_functions/collab/restore.md) |
| `/collab retract speak` | [collab/retract-speak.md](../_functions/collab/retract-speak.md) |
| `/collab rewrite execution` | [collab/rewrite-execution.md](../_functions/collab/rewrite-execution.md) |
| `/collab rewrite speak` | [collab/rewrite-speak.md](../_functions/collab/rewrite-speak.md) |
| `/collab rewrite summary` | [collab/rewrite-summary.md](../_functions/collab/rewrite-summary.md) |
| `/collab run plan` | [collab/run-plan.md](../_functions/collab/run-plan.md) |
| `/collab seal verification` | [collab/seal-verification.md](../_functions/collab/seal-verification.md) |
| `/collab set` | [collab/set.md](../_functions/collab/set.md) |
| `/collab show flags` | [collab/show-flags.md](../_functions/collab/show-flags.md) |
| `/collab show policy` | [collab/show-policy.md](../_functions/collab/show-policy.md) |
| `/collab show verdict` | [collab/show-verdict.md](../_functions/collab/show-verdict.md) |
| `/collab speak` | [collab/speak.md](../_functions/collab/speak.md) |
| `/collab unset` | [collab/unset.md](../_functions/collab/unset.md) |
| `/collab write summary` | [collab/write-summary.md](../_functions/collab/write-summary.md) |
| `/doc assess` | [doc/assess.md](../_functions/doc/assess.md) |
| `/doc compact` | [doc/compact.md](../_functions/doc/compact.md) |
| `/doc compare` | [doc/compare.md](../_functions/doc/compare.md) |
| `/doc write changelog` | [doc/write-changelog.md](../_functions/doc/write-changelog.md) |
| `/doc write manual` | [doc/write-manual.md](../_functions/doc/write-manual.md) |
| `/doc write readme` | [doc/write-readme.md](../_functions/doc/write-readme.md) |
| `/git commit` | [git/commit.md](../_functions/git/commit.md) |
| `/git issue` | [git/issue.md](../_functions/git/issue.md) |
| `/narrative rewrite content` | [narrative/rewrite-content.md](../_functions/narrative/rewrite-content.md) |
| `/quality assess game` | [quality/assess-game.md](../_functions/quality/assess-game.md) |
| `/quality assess interface` | [quality/assess-interface.md](../_functions/quality/assess-interface.md) |
| `/quality assess operations` | [quality/assess-operations.md](../_functions/quality/assess-operations.md) |
| `/quality assess web` | [quality/assess-web.md](../_functions/quality/assess-web.md) |
| `/quality show notes` | [quality/show-notes.md](../_functions/quality/show-notes.md) |
| `/quality tune` | [quality/tune.md](../_functions/quality/tune.md) |
| `/test` | [test/run.md](../_functions/test/run.md) |
<!-- END GENERATED:COMMANDS_ROSTER -->

Project onboarding files, such as `AGENTS.md` at an application repository root, are separate from this catalog. They describe the repo being edited, not global `~/.cursor` config.

## Maintainer QA

Run [_tests/commands](../_tests/commands.md) after any change in `commands/`, and run [_tests/_functions](../_tests/_functions.md) for changes in `_functions/`. The local contract covers public slash rosters, function rosters, links, headings, self-containment, rules alignment, and catalog sync.
