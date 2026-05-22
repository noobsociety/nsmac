# /doc compare

Compare original versus refined Markdown for preservation of facts, headings, and constraints; do not emit a compact final (use **`/doc compact`** after).

## Trigger

**Slash:** `/doc compare`
**Signature:** `/doc compare <path1> <path2>`
**Prose dispatch:** `(doc compare <path1> <path2>)` — prose routing hint; not a terminal command.
**Search phrases:** `compare markdown`, `compare versions`, `compare two docs`, `preservation check`, `diff markdown`

## Steps

1. Resolve `<path1>` from the first argument or first attachment; resolve `<path2>` from the second argument or second attachment. If either is missing, **ABORT**: list which argument(s) are missing.
2. If **`markdown-workflow.md`**, **`markdown-workflow.md`**, or (when the response needs a TOC) **`markdown-workflow.md`** is required and unreadable, **ABORT** per **`context-gate.md`**.
3. Compare `<path2>` (refined) to `<path1>` (original). Verify the refined text retains: facts, numbers, caveats, constraints, examples, definitions, key terms, and section headings.
4. Classify alignment as **faithful**, **partial**, or **misaligned**. List any missing or distorted material.
5. State whether the refined text is a reasonable base for compaction. Point to **`/doc compact`** when that is the logical next step.
6. Return a **comparison report** (structured bullets or short sections) and a **short note** on what changed and what remains at risk if compacting without fixes. Add no fact that appears in neither input.

## Notes

- **Parameters:** `<path1>` — original Markdown file (required); first attachment counts. `<path2>` — refined Markdown file (required); second attachment counts.
- TOC in the **response** only when the user asks or the report is explicitly TOC-shaped; placement after title/intro when used; follow **`markdown-workflow.md`**.

```route-arg
dispatch: (doc compare <path1> <path2>)
param: name=<path1>; required=required; placeholder=<path1>; class=type; rule=markdown file path or first attachment
param: name=<path2>; required=required; placeholder=<path2>; class=type; rule=markdown file path or second attachment
```
