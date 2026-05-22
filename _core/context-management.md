# Context engineering

Rules and commands are context injected into the model’s window on every relevant interaction. Effective context is specific, scoped, and audited; inefficient context dilutes signal and wastes tokens.

Contract: [style-guide.md](style-guide.md#llm-consumed-files), [document-standard.md](document-standard.md#llm-consumed-files), [command-standard.md](command-standard.md)

## Principles

### Signal over noise

Every line in a rule, command, or skill file goes to the model. Dead instructions, stale constraints, and vague guidance degrade output — the model treats them as patterns to replicate, not errors to skip. Remove any rule that no longer reflects actual behavior or requirements. Audit rules, commands, and skills on a regular cadence.

### Scope before writing

Determine the rule’s scope before writing a single instruction. A rule that applies to every file in every context is a token tax paid on every turn. Use path patterns to limit application to the files and paths the rule actually governs. Use `activation: false` for everything that is not genuinely universal.

### Specificity

Vague rules produce vague enforcement. State exactly what the model must do, must not do, and under what conditions.

Example (poor):

```text
Write good TypeScript.
Document code.
Handle async properly.
```

Example (better) — shape matches a TypeScript-scoped `markdown-workflow.md` rule such as `markdown-workflow.md` (illustrative):

```text
Apply on every edit and on every code suggestion when `*.ts` and `*.tsx` are in scope.
Never use `any`. Prefer `unknown` when the type is genuinely unknown.
Prefer ESLint v9 with flat config when the repository uses it.
```

## Writing rules

Rules (`markdown-workflow.md`) are persistent instructions the model applies when the rule’s scope matches the current context. The model follows the text literally. The model does not infer intent.

Writing standards — instruction format, ambiguity prevention, conflict resolution, and labeled examples — are defined in the [style guide](style-guide.md#llm-consumed-files).

### Scope declaration

Every rule file must state when the rule applies. A rule without an explicit scope condition silently applies to everything.

- **`auto-` rules (main):** set either `activation: true` and omit `path patterns`, or `activation: false` with path `path patterns` — never both. Each `auto-` rule is active globally when always-on, or when its path patterns match; it is not a dependency-only helper.
- **`shared-` rules (dependency):** keep `activation: false`. Load via Agent Requested, path `path patterns`, or references from other rules — they do not replace a main `auto-` rule for a domain.
- State the condition before the instruction in any conditional rule. Example from `markdown-workflow.md` (illustrative): “Applies when editing or suggesting `*.ts` and `*.tsx` in any repository (front matter path patterns).” Then follow with imperative behavior lines such as “Apply on every edit” and “Never use `any`.”

## Writing commands

Commands (`.md`) are step-by-step procedures the model executes on demand. Each command must accomplish one clearly bounded task.

### Structure

- Open with one sentence stating the command’s purpose and when to invoke it
- State the exact invocation syntax in the Trigger section — the model matches on the declared invocation string
- List steps as an ordered sequence. Each step is one action. Never group two actions in one step
- State edge cases and constraints in a Notes section

Catalog sync, **Trigger**/**Steps**/**Notes** order, slash **H1** alignment, and link hygiene for **`commands/*.md`** and **`_functions/**/*.md`** live in [command standard](command-standard.md).

### Precision

- Reference exact file paths, not vague descriptions: `markdown-workflow.md`, `markdown-workflow.md`, and `_functions/doc/write-readme.md` in the command config tree, not “the rules folder” or “the readme command”
- Name the tool or binary explicitly: `run npm run lint` when the workspace defines that script, or run the repository’s documented validation script when it ships one — not “run the checker”
- Specify the expected output: if the command produces a file, name the file and its destination path
- If a step depends on the result of a prior step, say so explicitly

### Phases

Separate brainstorming from execution in both the command design and the prompt that invokes it. A command that mixes planning and implementation produces confused, inconsistent output.

- Brainstorm commands gather information or generate options — they do not write files
- Execution commands write, modify, or delete — they do not ask open-ended questions mid-step
- Verification commands check, lint, or test — they do not apply fixes unless the command is explicitly a fix command

## Writing skills

Skills (`SKILL.md`) load when the model or user selects them. Apply the same signal, scope, and one-action-per-step discipline as commands. Per-type shape lives in the [document standard](document-standard.md#llm-consumed-files). Skills are delivered and versioned by the editor host; paths are not part of the `_core/` canon.

## Context budget

Rules, commands, and skills consume tokens whenever they are in play. Token cost compounds across long sessions and across the number of active rules.

### Reducing cost

- Keep every `*.md` and `markdown-workflow.md` under the config root within the **File size discipline** limits below; split or trim when a file outgrows them
- Prefer path-scoped activation (`activation: false` with `path patterns` on an `auto-` rule, or a `shared-` dependency) over an `auto-` rule with `activation: true` when the guidance applies only to some paths or tasks — see [file naming](style-guide.md#file-naming)
- Remove instructions that duplicate what ESLint, TypeScript, Prettier, or the repo test runner already enforce when those tools are authoritative — those constraints are free at inference time (see `markdown-workflow.md` in the rules layer, illustrative, for the stack that tree assumes)
- Use the `Agent Requested` application mode for rules the model can decide to invoke based on context
- Prefer `@Files` and `@folder` in prompts over relying on `@codebase` — `@codebase` may summarize files, reducing context fidelity

### Audit cadence

- Remove or update any rule, command, or skill file not confirmed relevant in the last two months
- After a significant project change (new framework, refactored architecture, renamed paths), review all rules, commands, and skills for accuracy
- Dead rules are counter-example noise: the model may treat stale content as a valid pattern to replicate

### File size discipline

The **250-line** strict budget applies **only** to prose under the **config root** (`COMMAND_CONFIG_ROOT`; in this repository, the **repository root**). Count every `*.md` and `markdown-workflow.md` under that root — including **`rules/`**, **`commands/`**, **`_core/`**, and root-level markdown such as **`README.md`** or audit notes. It does **not** apply to application or library source outside that tree. Host load behavior can change between releases, so re-verify limits when upgrading.

- Keep every `markdown-workflow.md` in `rules/` at or under 250 lines so essential instructions stay within typical load windows
- Keep every command playbook (`*.md` in `commands/`) at or under 250 lines for the same default. Slash commands invoked from the palette may load in full while always-on rules may not — confirm for your host version
- Keep every canon file (`*.md` in `_core/`) and every other `*.md` at the config root at or under 250 lines for the same default

`SKILL.md` files live under the host skills directory (not under `COMMAND_CONFIG_ROOT` in the default layout); length and split guidance for skills live in the [document standard](document-standard.md#llm-consumed-files). Non-markdown manifests are outside this Markdown line budget.

Enforce the line budgets with scripts or CI on the command config tree where it is validated, rather than relying on discipline alone.

## _core/ file naming

Every file under `_core/` uses a `<topic>-<type>` two-word pattern. Both words are singular base-form nouns. Gerunds, past participles, and acronyms are not permitted in either position.

## Related documents

- [Style guide — file naming](style-guide.md#file-naming) — naming conventions for rules and commands, front-matter requirements.
- [Style guide — LLM-consumed files](style-guide.md#llm-consumed-files) — writing standards: imperative instructions, ambiguity, conflict resolution, examples.
- [Document standard](document-standard.md#llm-consumed-files) — per-type templates for rule (`markdown-workflow.md`), command (`.md`), and skill (`SKILL.md`) shape.
- [Command standard](command-standard.md) — extended **`commands/`** playbook contract.
- [Author voice](author-voice.md) — personal-account voice.
