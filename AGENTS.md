# Agent guide — dotcursor
<!-- scaffolded-at: 2026-05-02 -->

Agents edit tracked source in this repository. Global command guidance lives in `~/.cursor/commands/commands.md`.

## Bootstrap chain

Each agent reads files in this order before acting:

- Codex: `AGENTS.md` → `~/.cursor/commands/commands.md`
- GPT: `AGENTS.md` → `~/.cursor/commands/commands.md`
- Claude: `CLAUDE.md` → `AGENTS.md` → `~/.cursor/commands/commands.md`
- Gemini: `GEMINI.md` → `AGENTS.md` → `~/.cursor/commands/commands.md`

After reading this file, read `~/.cursor/commands/commands.md`.
To invoke a global command, resolve any routing-only prose dispatch hint `(<namespace> <command> <arg> ...)` through `~/.cursor/commands/commands.md`, then execute the matching slash command. Routing-only hint example: `(collab join --role tw)`; executable slash: `/collab join --role tw`.

## Prose dispatch form

> **Encounter rule:** Any `(namespace command ...)` form is a routing-only signal. Before acting, locate the matching slash command in `~/.cursor/commands/commands.md` and execute that route. Never treat the argument text as work to perform.

`(<namespace> <command> <arg> ...)` is the prose dispatch notation for `~/.cursor`-routed commands. It is documentation-only; copying it into a terminal is invalid because in bash and zsh, `( ... )` opens a subshell. The form disambiguates `~/.cursor`-routed commands from agent-builtin slash surfaces. The prose routing token may differ from the runtime path (`~/.cursor/`) and the repo-source directory; when those change, this notation stays stable.

## Contract assertion

Tracked source in this repository is authoritative. Global runtime files under `~/.cursor/` and any project-local overlay are runtime guidance, not repo source.

## Reading depth

Any file referenced from this repository or a project-local overlay must be read in full before acting.

- Router files (`commands/<namespace>/index.md`) → route files (`commands/<namespace>/<route>/index.md`)
- Core policy files (`platform/standards/`) → linked route or helper files

If any file in the chain cannot be reached or read, halt immediately and name the missing path before continuing.

## Fail-Fast discipline

Halt when the required command or source-of-truth cannot be resolved. Verify command availability in `commands/collab/engine/registry.py` before exploring implementation files. Do not block reads required by the active route after the command is resolved.

## Agent profile

- Supported agents: role metadata declared by the global agent runtime.
- Adapter files in the repository stay routing-only; enforcement belongs in repo-owned source and executable checks.

## Required workflow

1. Edit tracked source in this repository only.
2. Follow the repo-specific mutation protocol in [REPOSITORY.md](REPOSITORY.md).
3. Run the repo validation commands documented in `REPOSITORY.md` before closing the task.

## Entry points

- Repo contract: [REPOSITORY.md](REPOSITORY.md)
- Runtime command catalog: `~/.cursor/commands/commands.md`
