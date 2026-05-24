# Style guide

The style guide applies to all `.md` and `markdown-workflow.md` files across all projects and notes, except where [Personal account exception](#personal-account-exception) or [Changelog entries](#changelog-entries) says otherwise. Per-type templates for common shapes live in [the document standard](document-standard.md); slash playbook details live in [command standard](command-standard.md).

Contract: [document-standard.md](document-standard.md), [command-standard.md](command-standard.md), [context-management.md](context-management.md)

## Audience

The intended reader varies by document type: a collaborator for project docs, future self for notes, a general audience for devblog entries and other personal accounts (see Personal account exception). Write so every document is readable in one pass without prior context.

## Voice

### Tone

Direct and neutral. No enthusiasm, no apology, no filler. State what is true or what to do.

Do: `Read README.md for layout, then follow the numbered Setup steps.`
Don’t: `You'll want to check out the README when you get a chance — it has some useful stuff!`

### Person

Use the following person rules based on document type:

- Second person (`you`) for instructions and how-to content
- First person plural (`we`) in vision or decision docs where authorship is shared
- Personal accounts (see Personal account exception): person follows [the author voice guide](author-voice.md) — often first person singular (`I`), not neutral documentation
- Third person for reference docs, role docs, and course notes — the subject is always the thing itself, never a pronoun

Do: `The command playbook states the slash invocation in the Trigger section.`
Don’t: `This playbook states the slash invocation in the Trigger section.`

Do: `The maintainer owns the slash command catalog in commands/commands.md.`
Don’t: `You own commands/commands.md.` (in a role doc describing the role to others)

Never use `this`, `it`, or `that` as a subject in reference docs, role docs, or course notes. Repeat the noun.

### Tense

- Present tense for facts: `context-gate.md` in the rules layer (illustrative) sets `activation: true` with no path `path patterns`.
- Imperative for instructions: `Open commands/git/commit/index.md in the commands layer before drafting the commit message.`
- Future tense only for planned but unbuilt features: `The migration command will handle schema versioning once the playbook is written.`
- In personal accounts (see Personal account exception), future tense is also permitted for intentions: `Next week I'll focus on the auth flow.`

## Sentences

- The first sentence of every document is a single declarative statement. Never open with “This document…”, “Welcome to…”, or “This guide covers…”. Exception: `quality/*.md` route playbooks may open with a bold acronym label as the subject — see the **Command** (`.md`) template in [document standard](document-standard.md) for the exact shape.
- One idea per sentence. Split compound sentences at conjunctions.
- Plain words over jargon. If a technical term is necessary, use it without apology.
- No filler openers. Never start a sentence with “Note that”, “Please”, “Feel free to”, or “It’s worth mentioning”.

## Formatting

### Headings

- `H1` — document title only, one per file, noun phrase by default; slash playbooks and harness files follow their own title shape in [command standard](command-standard.md)
- `H2` — major sections
- `H3` — subsections only when a section needs internal structure
- No `H4` or deeper — restructure instead
- Sentence case always: `Available tools`, not `Available Tools`

### Lists

- Use a list when there are three or more parallel items
- Use a numbered list only when order matters
- Each list item is a complete thought — no trailing ellipsis, no continuation into prose
- No nested lists beyond one level

### Emphasis

- `code` for file paths, commands, flags, identifiers, and values
- **Bold** sparingly — only for terms being defined, genuine warnings, or informal headings that intentionally fall outside the section hierarchy (e.g., a table of contents label)
- **Bold label colon rule:** add `:` only when the label introduces content that immediately follows — inline (`**Label:** text`) or as a block (`**Label:**` on its own line, block below). Omit `:` when the bold is a standalone label (e.g., a table cell, a section title with no following content, a pure heading)
- *Italic* for introducing a term the first time only, and for any tool, framework, or product name that has an associated hyperlink on its first mention — subsequent mentions of that linked keyword may remain italicized throughout the document
- No emphasis for decoration

### Horizontal rules

Use `---` only to separate structurally distinct blocks within a document — for example, surrounding a table of contents in a long entry. Never use horizontal rules as decoration or between ordinary sections.

### Tables

Use tables only for structured comparisons with three or more attributes. Label every column. No merged cells.

### Links

Use descriptive link text. Never “click here” or bare URLs in prose.

Do: `See the document standard for per-type templates.`
Don’t: `See here for more info.`

### Images

Use descriptive alt text that conveys content, not appearance. Add a caption only when the image needs context that the surrounding paragraph does not supply.

## What to omit

- Empty sections — if a section has nothing to say, remove the heading entirely
- Redundant content — if something is explained in another document, link to it instead
- Meta-commentary — never explain what the document is about to do; just do it
- Version history inside prose — use `CHANGELOG.md` for that (projects only)

## Personal account exception

Personal accounts — devblog entries, personal essays, journaling, public longform (blogs, feeds, essays), and narrative drafts — follow [the author voice guide](author-voice.md) instead of the standard voice rules. The formatting rules (headings, lists, code, links) still apply. Person and tense follow the voice guide (including first person where it is the default). Imperative mood does not apply.

## Changelog entries

`CHANGELOG.md` body lines are often generated from commit messages or sync scripts. Neutral tone and the person rules above do not apply to those machine-sourced lines. Section layout follows [the document standard](document-standard.md) and [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## LLM-consumed files

LLM-consumed files — rules (`markdown-workflow.md`), commands, and skills — follow all voice rules above plus the requirements in the LLM-consumed files section. These files instruct a language model, not a human. Ambiguity in these files produces inconsistent model behavior.

### Instructions

- Every behavioral instruction must be imperative: “Do X”, “Never Y”, “Always Z”
- Prefer “Never” over “Avoid where possible” — degree words create wiggle room the model will exploit
- One instruction per sentence. Do not combine two constraints into one sentence with “and”
- State the constraint before the reason: “Never edit generated files directly — regenerate them from source instead”, not the reverse

### Ambiguity

- A rule that can be read two ways will be read the wrong way. Rewrite until only one reading is possible
- Define terms the first time they appear. Do not assume the model shares your vocabulary
- Avoid pronouns with ambiguous referents: “it”, “this”, “that” — repeat the noun instead

### Conflict resolution

- When two rules could conflict, the more specific rule wins. State the precedence explicitly in the more general rule
- If a rule defers to another, name the other rule by filename: “See `markdown-workflow.md` for markdown and workflow precedence when rules stack” (as in `markdown-workflow.md`, illustrative)
- Never leave conflict resolution implicit — the model will not infer precedence correctly

### Examples

- Include at least one concrete example for any rule that describes output format or style
- Label examples explicitly: “Example:”, not inline without a label
- Show the correct case. Only show the incorrect case when the distinction is non-obvious

### Scope

- Every rule file must declare when the rule applies. Do not write rules that silently apply to everything
- If a rule applies only in certain conditions, state those conditions first before stating the rule

## File naming

### Rules (`markdown-workflow.md`)

Pattern: `markdown-workflow.md`

|Segment|Values                                   |Meaning                                                                                                                                                                                                                                 |
|-------|-----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|`scope`|`shared`, `auto`                         |`auto` — main rule for its domain (not a dependency). Use either `activation: true` or path `path patterns` with `activation: false`, never both. `shared` — dependency rule for other rules; keep `activation: false` and load via Agent Requested, path `path patterns`, or stacking — not as a standalone always-on main rule.|
|`group`|`docs`, `cmd`, `git`, `quality`, `review`, …|Domain that ties the rule to its command group. Matches the group prefix of related commands.                                                                                                                                           |
|`name` |kebab-case noun                          |What the rule governs within the group.                                                                                                                                                                                                 |

Examples: `markdown-workflow.md`, `markdown-workflow.md`, `quality-learning.md`

### Commands (`.md`)

Pattern: `commands/{namespace}/index.md` for public routers and `commands/{namespace}/{route}/index.md` for route playbooks.

The public router name matches the related command family and rule group. Route directory names stay route-shaped so the runtime does not expose them as standalone slashes.

Examples: `commands/git/commit/index.md`, `commands/quality/assess-game/index.md`, `commands/doc/write-readme/index.md`

### Other files

|Type           |Convention                                  |Example                                                                                            |
|---------------|--------------------------------------------|---------------------------------------------------------------------------------------------------|
|Standard docs  |SCREAMING_SNAKE                             |`AGENTS.md`, `README.md`, `MANUAL.md` (when the project ships one)                                 |
|Playbook docs  |SCREAMING_SNAKE                             |`VISION.md`, `PHASES.md`, role docs as the project names them                                      |
|Reference docs |kebab-case                                  |`AUDIT-meta.md` (filename at repository discretion)                                              |
|Skills         |`SKILL.md` inside named folder              |Host-assigned path under the editor’s skills directory (not part of the `core/framework/` canon tree)             |
|Devblog entries|`{n}-{slug}.md`                             |`1-week.md`, `0-foreword.md` (position 0 is reserved for the foreword; slug is fixed as `foreword`)|
|Course notes   |`notes-{variant}-{course}.md`               |`notes-full-domain-driven-design.md`                                                               |
|Test harnesses |`tests/<source-path>/<source-name>__<behavior>.test.sh`|`tests/core/collab/roles/roles__json_schema.test.sh`                          |

### JSON data files

Owned internal JSON data files use `camelCase` property names. This rule applies to all repository-owned JSON data files. Tool-governed config files — any JSON file whose keys are consumed or required by an external tool or runtime (editor settings, markdownlint config, VS Code keybindings) — keep the key names required by that tool.

Examples of owned internal JSON: `core/collab/roles/*.json` (`key`, `displayName`, `concerns`), `$HOME/.collabs/<projectId>/registry.json` (`activeCollabId`, `turnOrder`).

## Related documents

- [Document standard](document-standard.md) — per-type templates for each file shape.
- [Command standard](command-standard.md) — extended slash playbook rules.
- [Author voice](author-voice.md) — voice, register, and craft principles for personal accounts.
- [Context engineering](context-management.md) — context engineering principles and context budget guidance for rules and commands.

Install layout and runtime symlink behavior are out of scope for this `core/framework/` canon.
