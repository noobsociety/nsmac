# /commands

List public slash commands under `~/.cursor/commands/` and their route playbooks; use when you need canonical invocation syntax.

Contract: [platform/standards/command-standard.md](../platform/standards/command-standard.md)

## Trigger

**Slash:** `/commands`
**Phrases:** `command commands list`, `slash commands`, `what commands in commands/`, `commands-index`

## Steps

1. Read this table when the user needs the canonical name for a playbook or the list of installed slashes.
2. Open the public command file under `COMMAND_CONFIG_ROOT/commands/<namespace>/index.md` for routing behavior.
3. Open the linked route file under `COMMAND_CONFIG_ROOT/commands/<namespace>/<route>/index.md` for full route behavior.

## Notes

Public slash routers live at `commands/<namespace>/index.md`. Command route bodies live at `commands/<namespace>/<route>/index.md`.

Invoke routes as `/namespace route ...`; for example, `/doc write readme` loads `commands/doc/index.md`, resolves `write readme`, then executes `commands/doc/write-readme/index.md` with the remaining input and attachments.

`/test` may also require `~/.cursor/tests/specs/commands.md`, `~/.cursor/tests/specs/core.md`, `~/.cursor/tests/specs/settings.md`, and `REPOSITORY.md`.

**Invocation notes by command:**

- **`/agent <install | patch | upgrade>`** — install the multi-agent scaffold (`CLAUDE.md`, `AGENTS.md`, `REPOSITORY.md`) from `~/.cursor/platform/templates/` into the current repo, patch `REPOSITORY.md` with repo-specific mutation protocol and ownership rules, or upgrade installed scaffold files to the current templates; `install` aborts if any scaffold file already exists (pass `--force` to enter the diff-and-confirm path instead); `patch` aborts if `REPOSITORY.md` is absent or has no `<!-- TODO(patch): ... -->` placeholders; `upgrade` compares installed files against current templates and gates any overwrite.
- **`/collab <init | join | speak | retract speak | rewrite speak | advance | restore | set | unset | list | activate | open | reopen | close | remove participant | archive | delete | write summary | rewrite summary | run plan | export-issues | rewrite execution | show policy | show flags | show verdict | seal verification>`** — create, join, contribute to, retract or rewrite the last contribution, move between phases, reopen from non-success verdicts, rewrite execution records, edit or clear scoped metadata, manage active collabs, reopen/close, manage participants, soft-delete (archive) or permanently delete, write or rewrite summaries, run assigned action-plan items, record issue-terminal handoff evidence for a moderated collaboration record, read the gate policy, display the generated flag inventory or verdict metadata, or seal the `Completion.verification` sub-state after a reviewer pass; moderator-role contributions require human-authored text passed as `<message>` to `/collab speak` after joining with the moderator role.
  - **Retract.** `/collab retract speak` tombstones the current role's latest active-phase contribution while preserving original text for audit history.
  - **Seal.** `/collab seal verification` records the reviewer's `verificationSeal` object and triggers close or a cap-exit action (reopen-action-plan, reopen-handoff, archive); reviewer role only; zero verification rounds is a hard ABORT.
- **`/doc write readme`** — create or update repo `README*` or `readme*` files.
- **`/doc write manual`** — create or update repo-root `MANUAL.md` from traced automation.
- **`/doc write changelog <atomic | squash>`** — `atomic` or `squash` mode keyword required.
- **`/git commit <atomic | squash <from> <to>>`** — split working tree or squash an inclusive range.
- **`/git issue <create | implement> <goal>`** — create issue handoff or implement grounded work.
- **`/quality assess interface <image> <project>`** — screenshot UI review; attachment counts as `image`.
- **`/quality assess web <project>`** — web stack review.
- **`/quality assess game <project>`** — game engineering review.
- **`/quality assess operations <project>`** — build and operations review.
- **`/quality tune <interface | web | game | operations> ...`** — specialist pass plus cross-cutting Criteria audit.
- **`/quality show notes`** — internal route; loaded only by `/quality tune`; do not invoke directly.
- **`/test <commands | core | roles | settings | repo | all>`** — run one QA harness target or all in sequence.

**Advisory surface:** The system recommends but does not enforce; callers may invoke any route at any capability or effort level at their own discretion.

**Related principal workflows:**

| Route | Source of truth | Cross-stack |
| --- | --- | --- |
| `/quality assess interface` | `image` and `project` both required; attachment counts as `image`; with attachment first token is `project` | Screenshot-only by default. |
| `/quality assess web` | `project` — checked-in web tree | On Phaser repos: non-game aspects such as host, build, shell, BFF, and DOM outside canvas. |
| `/quality assess game` | `project` — game tree | On non-Phaser repos: game slice such as loop, canvas, and assets only. |
| `/quality assess operations` | `project` — checked-in build/ops tree | Owns `platform/tooling/`, Vite output/path correctness, and CI/deploy mechanics outside web/game/interface-owned surfaces. |

**Commands catalog:**

<!-- BEGIN GENERATED:COMMANDS_ROSTER -->
_Generated by `platform/tooling/sync-commands-catalog.sh`; do not edit this block by hand._

| Slash | Signature | Public router | Route playbooks |
| --- | --- | --- | --- |
| `/agent` | `/agent <install \| patch \| upgrade>` | [agent](agent/index.md) | [install](agent/install/index.md), [patch](agent/patch/index.md), [upgrade](agent/upgrade/index.md) |
| `/collab` | `/collab <init \| join \| speak \| retract speak \| rewrite speak \| advance \| restore \| set \| unset \| list \| activate \| open \| reopen \| close \| remove participant \| archive \| delete \| write summary \| rewrite summary \| run plan \| export-issues \| rewrite execution \| participant verify \| show policy \| show flags \| show verdict \| seal verification>` | [collab](collab/index.md) | [activate](collab/activate/index.md), [advance](collab/advance/index.md), [archive](collab/archive/index.md), [close](collab/close/index.md), [delete](collab/delete/index.md), [diff](collab/diff/index.md), [export-issues](collab/export-issues/index.md), [init](collab/init/index.md), [join](collab/join/index.md), [list](collab/list/index.md), [log](collab/log/index.md), [open](collab/open/index.md), [participant verify](collab/participant-verify/index.md), [remove participant](collab/remove-participant/index.md), [reopen](collab/reopen/index.md), [restore](collab/restore/index.md), [retract speak](collab/retract-speak/index.md), [rewrite execution](collab/rewrite-execution/index.md), [rewrite speak](collab/rewrite-speak/index.md), [rewrite summary](collab/rewrite-summary/index.md), [run plan](collab/run-plan/index.md), [seal verification](collab/seal-verification/index.md), [set](collab/set/index.md), [show flags](collab/show-flags/index.md), [show policy](collab/show-policy/index.md), [show verdict](collab/show-verdict/index.md), [speak](collab/speak/index.md), [status](collab/status/index.md), [unset](collab/unset/index.md), [write summary](collab/write-summary/index.md) |
| `/doc` | `/doc <write changelog \| write manual \| write readme>` | [doc](doc/index.md) | [write changelog](doc/write-changelog/index.md), [write manual](doc/write-manual/index.md), [write readme](doc/write-readme/index.md) |
| `/git` | `/git <commit \| issue>` | [git](git/index.md) | [commit](git/commit/index.md), [issue](git/issue/index.md) |
| `/quality` | `/quality <assess interface \| assess web \| assess game \| assess operations \| tune \| show notes>` | [quality](quality/index.md) | [assess game](quality/assess-game/index.md), [assess interface](quality/assess-interface/index.md), [assess operations](quality/assess-operations/index.md), [assess web](quality/assess-web/index.md), [show notes](quality/show-notes/index.md), [tune](quality/tune/index.md) |
| `/test` | `/test <commands \| core \| roles \| settings \| repo \| all>` | [test](test/index.md) | n/a |

| Route | Route playbook |
| --- | --- |
| `/agent install` | [agent/install/index.md](agent/install/index.md) |
| `/agent patch` | [agent/patch/index.md](agent/patch/index.md) |
| `/agent upgrade` | [agent/upgrade/index.md](agent/upgrade/index.md) |
| `/collab activate` | [collab/activate/index.md](collab/activate/index.md) |
| `/collab advance` | [collab/advance/index.md](collab/advance/index.md) |
| `/collab archive` | [collab/archive/index.md](collab/archive/index.md) |
| `/collab close` | [collab/close/index.md](collab/close/index.md) |
| `/collab delete` | [collab/delete/index.md](collab/delete/index.md) |
| `/collab diff` | [collab/diff/index.md](collab/diff/index.md) |
| `/collab export-issues` | [collab/export-issues/index.md](collab/export-issues/index.md) |
| `/collab init` | [collab/init/index.md](collab/init/index.md) |
| `/collab join` | [collab/join/index.md](collab/join/index.md) |
| `/collab list` | [collab/list/index.md](collab/list/index.md) |
| `/collab log` | [collab/log/index.md](collab/log/index.md) |
| `/collab open` | [collab/open/index.md](collab/open/index.md) |
| `/collab participant verify` | [collab/participant-verify/index.md](collab/participant-verify/index.md) |
| `/collab remove participant` | [collab/remove-participant/index.md](collab/remove-participant/index.md) |
| `/collab reopen` | [collab/reopen/index.md](collab/reopen/index.md) |
| `/collab restore` | [collab/restore/index.md](collab/restore/index.md) |
| `/collab retract speak` | [collab/retract-speak/index.md](collab/retract-speak/index.md) |
| `/collab rewrite execution` | [collab/rewrite-execution/index.md](collab/rewrite-execution/index.md) |
| `/collab rewrite speak` | [collab/rewrite-speak/index.md](collab/rewrite-speak/index.md) |
| `/collab rewrite summary` | [collab/rewrite-summary/index.md](collab/rewrite-summary/index.md) |
| `/collab run plan` | [collab/run-plan/index.md](collab/run-plan/index.md) |
| `/collab seal verification` | [collab/seal-verification/index.md](collab/seal-verification/index.md) |
| `/collab set` | [collab/set/index.md](collab/set/index.md) |
| `/collab show flags` | [collab/show-flags/index.md](collab/show-flags/index.md) |
| `/collab show policy` | [collab/show-policy/index.md](collab/show-policy/index.md) |
| `/collab show verdict` | [collab/show-verdict/index.md](collab/show-verdict/index.md) |
| `/collab speak` | [collab/speak/index.md](collab/speak/index.md) |
| `/collab status` | [collab/status/index.md](collab/status/index.md) |
| `/collab unset` | [collab/unset/index.md](collab/unset/index.md) |
| `/collab write summary` | [collab/write-summary/index.md](collab/write-summary/index.md) |
| `/doc write changelog` | [doc/write-changelog/index.md](doc/write-changelog/index.md) |
| `/doc write manual` | [doc/write-manual/index.md](doc/write-manual/index.md) |
| `/doc write readme` | [doc/write-readme/index.md](doc/write-readme/index.md) |
| `/git commit` | [git/commit/index.md](git/commit/index.md) |
| `/git issue` | [git/issue/index.md](git/issue/index.md) |
| `/quality assess game` | [quality/assess-game/index.md](quality/assess-game/index.md) |
| `/quality assess interface` | [quality/assess-interface/index.md](quality/assess-interface/index.md) |
| `/quality assess operations` | [quality/assess-operations/index.md](quality/assess-operations/index.md) |
| `/quality assess web` | [quality/assess-web/index.md](quality/assess-web/index.md) |
| `/quality show notes` | [quality/show-notes/index.md](quality/show-notes/index.md) |
| `/quality tune` | [quality/tune/index.md](quality/tune/index.md) |
<!-- END GENERATED:COMMANDS_ROSTER -->

Project onboarding files, such as `AGENTS.md` at an application repository root, are separate from this catalog. They describe the repo being edited, not global `~/.cursor` config.

## Maintainer QA

Run [tests/specs/commands](../tests/specs/commands.md) after any change in `commands/`. The local contract covers slash rosters, route rosters, links, headings, self-containment, rules alignment, and catalog sync.
