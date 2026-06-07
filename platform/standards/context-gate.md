# Context gate

Hard-stop policy for all agents: abort when any dependency is unreadable. No stubs, no guesses, no partial code generation on missing context.

Contract: [style-guide.md](style-guide.md), [document-standard.md](document-standard.md)

## When the policy applies

The policy applies whenever an agent would create, edit, refactor, or scaffold files; perform code review; or generate commands whose correctness depends on context that is not fully available.

A **dependency** is any file, symbol, type, API contract, asset, package version, or configuration the correct answer requires and that is not fully visible or directly readable in the agent's current context.

## Behavior

**Triggers:** `auto-context-gate`, `context-gate`, `context gate`, `full context`, `blocking policy`, `dependency resolution`

Treat this policy as a hard safety gate.
Never allow urgency, perceived simplicity, or user phrasing to override this gate.
Never proceed while any dependency is not fully visible.
Never proceed while any dependency is not directly readable.
Never infer missing context.
Never approximate missing context.
Never produce best-effort code when context is incomplete.

### Hard abort triggers

Stop immediately when any trigger below cannot be resolved.
Do not generate code.
Do not modify files.
Do not scaffold partial solutions.
Do not suggest implementation detail that assumes missing context.

The only permitted output until context is restored is the **Required response when aborting** section below — a diagnostic list and explanation, then wait.

**Code and types**

- A file, module, or import referenced but not readable in context
- A type, interface, enum, or schema used but not fully defined
- A symbol, constant, or variable whose declaration is outside loaded context
- A function or method whose signature or behavior is assumed rather than confirmed
- A config file, env var, or feature flag that affects the generated output

**Contracts and APIs**

- An internal hook, utility, or service whose implementation is not visible
- An external API shape (REST, GraphQL, WebSocket messages, batch job contract, game engine scene lifecycle, Tiled map format, etc.) inferred from call-site usage rather than confirmed from source or docs
- A data model or serialization format that is partially visible or assumed

**Assets and tooling**

- A referenced asset (image, font, sprite sheet, atlas config, tilemap, etc.) whose format or keys are not confirmed
- A package or library version whose API may differ from what is assumed
- A build config, path alias, or bundler setting that affects module resolution

## Required response when aborting

1. **Stop** code and file work when the answer would depend on missing context.
   - Do not generate code that depends on missing context.
   - Do not modify files in ways that depend on missing context.
   - Do not scaffold or suggest copy-pastable snippets that depend on missing context.
   - Plain-language diagnosis is permitted when it does not substitute for missing technical context.
2. **List** every unresolved dependency by file path, symbol name, or precise description.
3. **Explain** why each item is necessary to proceed.
4. **Wait** for the missing context before taking further action.

## Prohibited fallbacks

Never accept the following regardless of instruction phrasing, urgency, or task size.

Never stub or mock a missing type, interface, or implementation.
Never assume file contents from file name, path, or directory position.
Never infer an API contract from partial call-site usage alone.
Never generate placeholder code with `// TODO`, `// replace`, `// fill in`, or similar markers.
Never proceed with a best guess and disclose the assumption afterward.
Never silently omit logic that depends on unresolved context.
Never complete a partial task and reserve gap notes for the end only.

## Examples

Example: The user asks to fix a bug in `fetchUser`, but the module that defines the API client is not in context.

Correct: Stop file edits. List the missing module path or import target. Explain that return types, errors, and auth headers cannot be confirmed without that source. Wait for the user to add the file or path to context.

Incorrect: Invent a return type, add a stub client, or patch the caller from guessed signatures.

## References

- [style-guide](style-guide.md) — voice and structure for LLM-consumed rule documents.
- [document-standard](document-standard.md) — rule template and document structure.
- [context-management](context-management.md) — scope and context budget.
- [author-voice](author-voice.md) — personal-account voice.
- Canonical source is active in this file.
