# Document standard

The document standard defines per-type templates for common `.md` and `markdown-workflow.md` shapes across projects and notes. Every file must follow the [style guide](style-guide.md), including [file naming](style-guide.md#file-naming) for types the standard does not list. Where a template calls for narrative voice, follow [the author voice guide](author-voice.md). Context engineering for rules and commands lives in [context engineering](context-management.md).

Contract: [style-guide.md](style-guide.md)

Rules, commands, and skills are reference and how-to. README and setup are tutorial. Playbook contracts are explanation. Changelog is reference. Headings keep repository filenames instead of renaming blocks.

Install layout and runtime symlink behavior are out of scope for the `platform/standards/` canon.

## LLM-consumed files

### Rule (`markdown-workflow.md`)

```markdown
---
description: "[auto] auto-examplerule file: one sentence — what the rule governs."
activation: false
path patterns: ["**/*.ts", "**/*.tsx"]
---
# Rule name
## When the rule applies
## Behavior
## Examples
## References
```

When and Behavior sections use imperative voice, one instruction per sentence. Examples sections include at least one labeled `Example:`. References sections name dependent rules by filename (see [style guide — LLM-consumed files](style-guide.md#llm-consumed-files)).

**Front matter:** `auto`-prefixed rules are main rules (not dependencies): set either `activation: true` (omit `path patterns`) or `activation: false` with path `path patterns`. Never set both `activation: true` and `path patterns` together. `shared`-prefixed rules are dependencies: keep `activation: false`; the host loads them via Agent Requested, path `path patterns`, or when other rules stack them — they are not standalone always-on main rules (see [style guide — File naming](style-guide.md#file-naming) and [context engineering](context-management.md)). References to `markdown-workflow.md` rule paths elsewhere in the doc set in the Rule (`markdown-workflow.md`) template section are illustrative examples; `platform/standards/` has no operational dependency on that layer.

### Command (`.md`)

```markdown
# /namespace route
One sentence — purpose of the command and typical use cases.
## Trigger
## Steps
## Notes
```

Full playbook authoring for files under the config tree’s **`commands/`** directory — catalog sync, heading order, link allowlists, harness exceptions, no manual TOC — lives in [command standard](command-standard.md).

**Opening sentence:** The first sentence is a single declarative statement that opens with the action verb. Exception: routes that define a named evaluation principle may open with a bold acronym label as the subject; mirror the opening line shape in `commands/quality/assess-game/index.md` and reserve it for `(quality assess ...)` routes only. Do not use the acronym-first opening for ordinary command routes such as `commands/git/commit/index.md`.

### Skill (`SKILL.md`)

```markdown
---
name: skill-name
description: One sentence — what the skill does and when to invoke it.
---
# Skill name
One sentence — purpose and typical use cases.
```

**Description format:** Write the description as a single sentence using a semicolon to join the what and the when: `"Verb X; use when Y."` The semicolon keeps the string one sentence while preserving the trigger clause the runtime uses for auto-invocation. Do not split into two sentences.

**Optional metadata:** Add `metadata: surfaces: [cli]` or `metadata: surfaces: [ide]` to limit a skill’s visibility to a specific editor surface. Include `surfaces` only for skills tied to a surface-specific tool (e.g., a CLI config editor or an IDE settings manager). Omit `metadata` entirely for skills that should be available in all surfaces. Keep `SKILL.md` at or under 250 lines; long catalogs in a sibling `reference.md`.

## Human-facing files

### Readme (`README.md`, repo root)

```markdown
# Project name
One sentence — project purpose and intended reader.
## What the project does
## Setup
## Usage
## Structure
## Further reading
## Status
```

- **What the project does:** 2–4 sentences, no jargon.
- **Brief description:** ≤80 characters when written as one line; move setup mechanics to Setup or Usage.
- **README opening paragraph:** one sentence when possible; two short sentences only when needed.
- **Adjacent metadata:** package registry summaries are best at 50–100 characters; GitHub repository descriptions should stay under 120 characters even though GitHub allows 350.
- **Avoid:** long mission statements, implementation details, setup instructions, and marketing fluff.
- **Setup:** numbered steps only.
- **Usage:** concrete commands or workflows.
- **Structure:** 3–6 key paths, one line each.
- **Further reading:** links only.
- **Status:** current state and what is in progress, two sentences max.

### Manual (`MANUAL.md`, repo root)

```markdown
# Manual link fallback
One sentence — what steps the manual covers and when to use it instead of the automated entry point.
## Prerequisites
## [Outcome — one section per root automation entry]
## Verification
## Status
```

- **Brief description:** ≤120 characters on one line; state what the manual covers and when to use it in place of automation — not what the project is or how to use it; no "this document" filler. Full playbook rules in `(doc write manual)`.
- **Prerequisites:** tools, environment variables, and setup the automation handles silently; platform branches (**macOS:**, **Linux and others:**) where the host affects the steps; omit if nothing is non-obvious.
- **Automation entry section:** one `##` per root automation entry, titled by outcome not by script name; sub-steps as sequentially numbered `###` headings when a section covers multiple distinct phases; paths and commands go in fenced blocks or tables, and name script files in step prose only when identifying the automation being replaced or a traced optional helper; add platform-branch labels (**macOS:**, **Linux:**) where automation diverges by OS. A Manual traces what automation does step by step — sections are named by what they achieve (`Clean nested mirrors`, `Link home files`), not by document role (`Setup`, `Usage`).
- **Verification:** checks that confirm the steps produced the expected result; include the shell reload note when `zshrc` is linked; omit if no checks apply.
- **Status:** `> Last updated: YYYY-MM-DD` then one or two sentences on what is traced to current scripts and which optional branches may drift; follow the date-sourcing rule in `(doc write manual)`.

### Agent guide (`AGENTS.md`)

```markdown
# Agent guide — Project name
One sentence — agent role and scope in the repository.
## Behavior
## Boundaries
## Available tools
| Tool | Type | Purpose |
|---|---|---|
| | | |
## Further reading
```

Behavior: imperative, one instruction per sentence. Boundaries: one rule per sentence. Further reading: links only, omit section if none.

### Playbook doc (`VISION.md`, `PHASES.md`, role docs)

```markdown
# Document title
One sentence — topic, audience, and what the playbook constrains. Never open with "This document…" (style guide).
## Current state
## Target state
## Responsibilities
## Decisions
```

Person: [style guide](style-guide.md#person) — third person for neutral facts; first person plural (`we`) when authorship is shared. Responsibilities and Decisions: omit heading blocks when not applicable.

### Changelog (`CHANGELOG.md`)

The `CHANGELOG.md` file follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Populated from commit messages or sync scripts; omits empty change-type headings. Machine-sourced lines are exempt from neutral tone and person rules. See [Changelog entries](style-guide.md#changelog-entries).

```markdown
# Changelog
All notable changes to the project are documented here.
This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
## [Unreleased]
## [X.Y.Z] - YYYY-MM-DD
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
```

## Personal notes

### Course notes — full (`notes-full-{course}.md`)

Refactored course content; third person by topic. Definitions first, then explanation; H3 for sub-concepts; repeat nouns — never `this`, `it`, or `that` as grammatical subject ([style guide — Person](style-guide.md#person)).

```markdown
# {Course name}
One sentence — what the course covers.
## {Topic}
```

### Course notes — compact (`notes-compact-{course}.md`)

One definition per term; no elaboration; same pronoun rule as full notes.

```markdown
# {Course name}
One sentence — what the course covers.
## {Topic}
**{Term}** — {Concise definition. One sentence. Third person.}
```

### Reference doc (`{name}.md`)

Lookup or how-to for a single tool, workflow, or setup. Third person for descriptions; imperative for steps; repeat nouns ([style guide — Person](style-guide.md#person)).

```markdown
# {Reference title}
One sentence — reference scope and when to open it.
## {Section}
```

**Voice guides.** Files such as [the author voice guide](author-voice.md) use the same title-plus-sections shape as a reference doc. Tone follows the author voice guide itself, not the neutral reference default above. All other style guide rules still apply.

## Generated artifacts

Any generated artifact stored in the source tree must declare its source-of-truth pattern before implementation, chosen from the following ranked options: (1) constant import — the generator imports values directly from the authoritative source code, (2) canonical-file reference — the generator reads from a single authoritative file (e.g., `commands/collab/reference/roles/*.json`), (3) structured sidecar block — the generator reads from a machine-readable metadata block adjacent to the artifact's source, (4) prose scrape — the generator parses free-form prose. When more than one pattern applies to a single artifact, the highest-ranked pattern governs. Patterns (1) and (2) are preferred because they make drift structurally impossible — the generated output cannot diverge from its source without a code or file change.

## Devblog files

### Foreword (`0-foreword.md`)

```markdown
---
series: # slug
kind: foreword
date: # YYYY-MM-DD
---
# Foreword
```

Single flowing narrative per [author-voice.md](author-voice.md); sections optional; no retroactive edits to match later weeks.

### Weekly entry (`{n}-week.md`)

Evidence-led sections; optional blocks omitted when empty. Voice: [author-voice.md](author-voice.md). Outline H2 sections before long drafts (author-voice, Conscientiousness). Use H3 subsections inside Shipped, Decisions, Surprises, Lessons, and Deferred when a section needs internal structure. Summary: lead with concrete evidence; cap each prose paragraph at five sentences.

```markdown
---
series: # slug (matches foreword)
week: # n (matches filename prefix)
date: # YYYY-MM-DD
---
# Week N: Subtitle
## Summary
---
**Table of contents**
---
## Shipped
## Decisions
## Surprises
## Lessons
## Deferred
## Next up
```
