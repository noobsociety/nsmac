# NoobSociety Multi Agent Collaboration

[![CI](https://github.com/noobsociety/nsmac/actions/workflows/ci.yml/badge.svg)](https://github.com/noobsociety/nsmac/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

A routed command and agent-harness framework for NoobSociety multi-agent collaboration.

NSMAC (NoobSociety Multi Agent Collaboration) defines the routes, roles, records, and validation
gates that agents use to coordinate work. NSMAC packages the adapter guides, command catalog,
collaboration playbooks, registry helpers, standards, generated references, and repository QA
harness for that workflow.

## Contents

- [Install](#install)
- [Quick start](#quick-start)
- [Command surface](#command-surface)
- [Documentation](#documentation)
- [Runtime state](#runtime-state)
- [Quality](#quality)
- [Repository layout](#repository-layout)
- [Development](#development)
- [Versioning and releases](#versioning-and-releases)
- [License](#license)

## Install

Clone NSMAC into a local checkout when that directory does not already exist.

```bash
git clone https://github.com/noobsociety/nsmac.git ~/nsmac
```

For an existing checkout that should sync to the NoobSociety repository:

```bash
cd ~/nsmac
git remote set-url origin https://github.com/noobsociety/nsmac.git
git fetch origin --prune --tags
git branch --set-upstream-to=origin/main main
```

Install local git hooks after cloning or rebinding the checkout:

```bash
~/nsmac/platform/tooling/install-git-hooks.sh
```

## Quick start

Run the repository gate:

```bash
./tests/run.sh
```

Agent adapters bootstrap through the command catalog:

| Adapter | For | Bootstrap chain |
| --- | --- | --- |
| `CLAUDE.md` | Claude Code CLI | `CLAUDE.md` -> `AGENTS.md` -> `commands/commands.md` |
| `AGENTS.md` | Codex, GPT, and other agent harnesses | `AGENTS.md` -> `commands/commands.md` |

Use routed command forms inside an agent session, not as shell commands:

```text
(collab init "Dispatch Surface Polish")
(collab join --role tw)
(collab speak)
(collab status)
```

## Command surface

NSMAC publishes command routes and helper contracts instead of package exports. The public command
catalog lives in [`commands/commands.md`](commands/commands.md).

| Surface | Purpose |
| --- | --- |
| `(commands)` | List public command routes and route playbooks |
| `(agent <route>)` | Install or update downstream agent scaffolds |
| `(collab <route>)` | Run collaboration lifecycle, transcript, verification, tagging, and issue-planning routes |
| `(test <target>)` | Run Markdown-facing harness targets |

Route bodies live under `commands/<namespace>/<route>/index.md`. Cross-route policy lives under
`platform/standards/`, and executable backing helpers live under each namespace's engine
directory.

## Documentation

Start with [`platform/reference.md`](platform/reference.md) for the system map. Generated mirrors
under [`generated/`](generated/) expose the command reference, lifecycle projection, registry CLI
surface, and content invariants. Edit their source inputs instead of editing generated files by hand.

The main source contracts are:

| Document | Purpose |
| --- | --- |
| [`REPOSITORY.md`](REPOSITORY.md) | Repository authority, mutation, validation, and reporting contract |
| [`commands/commands.md`](commands/commands.md) | Public command catalog and dispatch routing |
| [`platform/reference.md`](platform/reference.md) | System-level navigation map |
| [`platform/standards/runtime-contract.md`](platform/standards/runtime-contract.md) | Host prerequisites |

## Runtime state

`$HOME/.collabs/<projectId>/` stores live collaboration records and transcripts for this repository.
The tracked `.collab.json` marker binds this checkout to the readable project id `nsmac`.

Runtime state is intentionally excluded from git. Source lives in this repository; generated mirrors
live under `generated/`; local runtime payloads such as agent runtime directories, tracking payloads,
`argv.json`, `projects/`, `extensions/`, `ide_state.json`, `plugins/`, `skills/`, `plans/`, and
`subagents/` remain ignored. Legacy host skill-cache payloads are also ignored by the repository
allowlist.

## Quality

The GitHub Actions CI workflow runs the repository gate:

```bash
./tests/run.sh
```

The test runner starts with `./platform/tooling/audit.sh`, then runs the
retained test manifest.

Before opening a pull request or pushing main, run:

```bash
./tests/run.sh
```

## Repository layout

| Path | Purpose |
| --- | --- |
| `CLAUDE.md` | Claude Code adapter |
| `AGENTS.md` | Codex, GPT, and other agent-harness adapter |
| `REPOSITORY.md` | Source authority and validation contract |
| `.collab.json` | Tracked collab project marker |
| `.github/workflows/` | Repository CI workflow |
| `commands/` | Command catalog, routers, route playbooks, namespace data, and helpers |
| `commands/collab/` | Collaboration routes, registry engine, references, and advisory data |
| `platform/` | Shared standards, tooling, templates, and data |
| `generated/` | Tool-generated command and lifecycle mirrors |
| `registry.schema.json` | Reference registry schema projection |
| `tests/` | Shell and Markdown-facing QA harnesses |

## Development

Use the host prerequisites in [`platform/standards/runtime-contract.md`](platform/standards/runtime-contract.md):
Python 3.9 or newer, bash 3.2 or newer, `git`, `python3`, and POSIX shell utilities on `$PATH`.
Python tooling uses only the standard library.

Generated files are produced by platform tooling and checked by the audit. Do not edit these by
hand:

- files under `generated/`
- the generated command roster block in `commands/commands.md`

Run focused checks only when working on a narrow surface, then finish with the repository gate:

```bash
./platform/tooling/audit.sh
./platform/tooling/sync-commands-catalog.sh --check
./tests/run.sh
```

See [`REPOSITORY.md`](REPOSITORY.md) for ownership boundaries and reporting requirements.

## Versioning and releases

NSMAC does not publish an npm package. Repository snapshots are anchored with weekly tags that use a
year-week naming pattern.

Collab-specific tagging is explicit and dry-run first:

```text
(collab tag)
```

The tag route is lifecycle-adjacent tooling. It does not run automatically from `(collab close)`.

## License

NSMAC is released under the [MIT License](./LICENSE). MIT was selected using the guidance at [Choose
a License](https://choosealicense.com/licenses/mit/) because it permits broad reuse with attribution
and warranty disclaimers.

Only add third-party code, assets, or documentation when the license is compatible with MIT and the
source is documented in the relevant change.
