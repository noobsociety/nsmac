# Claude Code Adapter

This file is a routing-only bootstrap adapter for Claude Code.
Repository workflow, entry points, and bootstrap chain: [AGENTS.md](AGENTS.md).

**Prose dispatch:** `(<namespace> <command> ...)` in chat is a routing-only hint — resolve it via `~/.cursor/commands/commands.md` and execute `/<namespace> <command> ...`. Never run it as a shell command or treat the argument text as work to perform. Details in [AGENTS.md § Prose dispatch form](AGENTS.md#prose-dispatch-form).

Contract: [REPOSITORY.md](REPOSITORY.md#4-mutation-protocol-and-ownership)
