# /doc write manual

Author or update **only** repo-root `MANUAL.md`: numbered human steps that mirror what automation does, so a reader never needs to run those scripts.

## Trigger

**Slash:** `/doc write manual`
**Signature:** `/doc write manual`
**Prose dispatch:** `(doc write manual)` — prose routing hint; not a terminal command.
**Search phrases:** `update manual`, `create manual`, `manual fallback`, `recovery guide`, `MANUAL.md`

## Steps

1. Confirm the sole target is **`MANUAL.md` at the repository root** beside **`README.md`**. Do not edit README, changelog, or other paths from this command unless the user explicitly names them in a separate task.
2. If **`markdown-workflow.md`**, **`markdown-workflow.md`**, or **`markdown-workflow.md`** is required for formatting and is not readable, **ABORT** per **`context-gate.md`**.
3. Choose **Create** (no file yet or user wants a new manual) or **Update** (file exists). Default to **Update** when unsure; preserve structure unless the user requests a rewrite.
4. Read automation in order: root operational entrypoints (shell installers, `Makefile`, `justfile`, …) whole or enough to list side effects; scripts they call; configs and manifests those scripts read; optional CI for enforced commands; existing **`MANUAL.md`** last (may be wrong—verify against scripts). If there is no shell automation, document only what exists and trace that source the same way.
5. For each automated action, tie every documented command and path to a traced line or construct in the scripts. Never invent steps not evidenced in the source. Label platform branches (**macOS:**, **Linux:**, …) when scripts branch on OS.
6. Build **`MANUAL.md`** sections: **Title (H1)** always; **Brief description** always (≤120 characters on one line if one sentence; two short sentences allowed; state what the manual covers and when to use it instead of automation; no vague “this document” filler); **Table of contents** required for this workspace's repo-root **`MANUAL.md`**, wrapped with `---` immediately before the `**Table of contents**` label and immediately after the final TOC entry; **Prerequisites** when tools or env vars are non-obvious and scripts reference them; **one `##` section per root automation entry** (title describes outcome, not filename; name script files in numbered step prose only when identifying the automation being replaced or a traced optional helper; paths may appear inside fenced commands copied from traced behavior); optional **Verification** when checks are evidenced; **Status** always (see **Notes**).
7. Use imperative mood for steps; sentence-case headings; fenced blocks with language tags; plain Markdown without decorative horizontal rules except an optional TOC band per **`markdown-workflow.md`**.
8. On **Update**, re-trace changed scripts, sync headings and steps, sync TOC if present, refresh **Status** when meaning changes.
9. Before finishing, verify each of the following. Every numbered step and fence maps to a traced source. Filename mentions in step sentences are limited to the replaced automation or traced optional helpers. The **Status** date follows **Date sourcing** in **Notes**. The TOC lists every `##`, `###`, and deeper heading, or follows the label-only rule from **`markdown-workflow.md`**. Markdown structure and voice follow **`markdown-workflow.md`** through **`markdown-workflow.md`**. No edits exist outside repo-root **`MANUAL.md`**.

## Notes

- **Voice:** Imperative for steps; neutral declarative for short explanations. Shared markdown rules apply; this command owns procedural clarity on **`MANUAL.md`**.
- **README pairing:** README often carries orientation and short install; **`MANUAL.md`** carries traced fallback steps. Do not invoke **`/doc write readme`** from this command. Link normally when the repo already cross-links.
- **Changelog:** Do not create or edit **`CHANGELOG.md`** unless the user or task explicitly includes it.
- **Relative paths:** Examples show markdown as it should appear in target **`MANUAL.md`**; links to **`README.md`** are repo-root relative.
- **Status template (default):**

```markdown
## Status

> Last updated: YYYY-MM-DD

What is verified against current scripts and what may still drift (two sentences max).
```

- **Date sourcing:** Never guess **`YYYY-MM-DD`**. Prefer `date +%F` in the workspace shell; otherwise use a calendar date the user states for this edit; if neither exists, ask once for permission to run `date +%F` or for the date.
- **Structure table (condensed):** **Title** and **Brief description** always; **TOC** required for this workspace's repo-root **`MANUAL.md`**; **Prerequisites** if needed; **one `##` per root automation entry** always when automation exists; **Verification** if applicable; **Status** always.
- **Compliance gate:** No section without traced evidence; no README or changelog edits from this command; procedural claims must map to scripts and configs the assistant read.
