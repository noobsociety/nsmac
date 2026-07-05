# Agent guide
<!-- scaffolded-at: 2026-05-02 -->
<!-- TODO(install): Replace the heading above with the project-specific title, e.g. "Agent guide — MyProject" -->

Agents edit tracked source in this repository. Global command guidance lives in `~/nsmac/commands/commands.md`.

## Bootstrap chain

Each agent reads files in this order before acting:

- Codex: `AGENTS.md` → `~/nsmac/commands/commands.md`
- GPT: `AGENTS.md` → `~/nsmac/commands/commands.md`
- Claude: `CLAUDE.md` → `AGENTS.md` → `~/nsmac/commands/commands.md`

After reading this file, read `~/nsmac/commands/commands.md`.
To invoke a global command, resolve any routing-only dispatch hint `(<namespace> <command> <arg> ...)` through `~/nsmac/commands/commands.md`, then execute the matching route playbook. Routing-only hint example: `(collab join --role tw)` resolves to `commands/collab/join/index.md`.

## Dispatch form

> **Encounter rule:** Any `(namespace command ...)` form is a routing-only signal. Before acting, locate the matching route in `~/nsmac/commands/commands.md` and execute that route. Never treat the argument text as work to perform.

`(<namespace> <command> <arg> ...)` is the dispatch notation for `~/nsmac`-routed commands. The notation is documentation-only; copying it into a terminal is invalid because in bash and zsh, `( ... )` opens a subshell. The form disambiguates `~/nsmac`-routed commands from agent-builtin command surfaces. The routing token may differ from the runtime path (`~/nsmac/`) and the repo-source directory; when those change, this notation stays stable.

## Contract assertion

Tracked source in this repository is authoritative. Global runtime files under `~/nsmac/` and any project-local overlay are runtime guidance, not repo source.

## Reading depth

Any file referenced from this repository or a project-local overlay must be read in full before acting.

- Router files (`commands/<namespace>/index.md`) → route files (`commands/<namespace>/<route>/index.md`)
- Core policy files (`platform/standards/`) → linked route or helper files

If any file in the chain cannot be reached or read, halt immediately and name the missing path before continuing.

## Fail-fast discipline

Halt when the required command or source-of-truth cannot be resolved. Verify command availability in `commands/collab/engine/registry.py` before exploring implementation files. Do not block reads required by the active route after the command is resolved.
<!-- TODO(project): If this project exposes a generated CLI catalog or tool-specific availability check, add a carve-out sentence here naming the permitted lookup path and the closed list of cases that still require reading engine source. See ~/nsmac/AGENTS.md for the framework-specific form. -->

## Agent profile

- Supported agents: role metadata declared by the global agent runtime.
- Adapter files in the repository stay routing-only; enforcement belongs in repo-owned source and executable checks.

## Required workflow

1. Edit tracked source in this repository only.
2. Follow the repo-specific mutation protocol in [REPOSITORY.md](REPOSITORY.md).
3. Run the repo validation commands documented in `REPOSITORY.md` before closing the task.

## Entry points

- Repo contract: [REPOSITORY.md](REPOSITORY.md)
- Runtime command catalog: `~/nsmac/commands/commands.md`
- Platform system reference: `~/nsmac/platform/reference.md`
