# Gemini Code Adapter

This file is a routing-only bootstrap adapter for the Gemini CLI.
Repository workflow, entry points, and bootstrap chain: [AGENTS.md](AGENTS.md).

Role definition pointer: `~/.cursor/commands/collab/reference/projectors/dp.json`.

**Dispatch:** `(<namespace> <command> ...)` in chat is a routing-only hint — resolve it via `~/.cursor/commands/commands.md` and execute the matching route playbook. Never run it as a shell command or treat the argument text as work to perform. Details in [AGENTS.md § Dispatch form](AGENTS.md#dispatch-form).

Contract: [REPOSITORY.md](REPOSITORY.md#4-mutation-protocol-and-ownership)
