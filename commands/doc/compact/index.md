# /doc compact

Compact a Markdown document while preserving all facts, structure, and constraints, and return the result with a short change note.

## Trigger

**Slash:** `/doc compact`
**Signature:** `/doc compact <path>`
**Prose dispatch:** `(doc compact <path>)` — prose routing hint; not a terminal command.
**Search phrases:** `compact markdown`, `compare then compact`, `tighten markdown`, `shrink doc`

## Steps

1. Resolve `<path>` from the first argument or attachment. If missing, **ABORT**: `<path>` is required.
2. If **`markdown-workflow.md`**, **`markdown-workflow.md`**, or (when a TOC is in play) **`markdown-workflow.md`** is required and unreadable, **ABORT** per **`context-gate.md`**.
3. Run the same **preservation check** as **`/doc compare`**: refined (or working copy) must retain facts, numbers, caveats, constraints, examples, definitions, key terms, and headings. Restore gaps before finalizing.
4. Execute steps 4a–4e in order:
   - **4a.** Duplicate the resolved document in memory as a working copy.
   - **4b.** Compact the working copy.
   - **4c.** Compare the working copy to the original using the preservation check from step 3.
   - **4d.** Repeat 4b–4c until the preservation check passes or **five** compaction passes complete; if still failing, return the last working copy, list preservation gaps, and stop.
   - **4e.** Return the working copy. Do not overwrite the source file unless the user explicitly requests an in-place update.
5. Default to **response-only** output. Return the **final refined text** and a **short note** (bullets or two to three sentences) on what changed and why.

## Notes

- **Parameters:** `<path>` — Markdown file path (required); attachment is equivalent.
- **Force flag:** `--force` is ineligible for this route per [core/framework/command-argument.md](../../../core/framework/command-argument.md). Step 4e is a default output-mode choice, not an artifact-conflict guard; `--force` on this route would teach users that the flag means "change behavior" rather than "overwrite an artifact."
- **TOC:** Do not add by default. Preserve an existing TOC unless the user asks to drop it. Add only when the user asks; follow **`markdown-workflow.md`**; place after title and short intro when present.
- Do not add content beyond what the original supports.

```route-flag
flag: force
eligibility: ineligible
guard-class: output-mode-policy
ineligibility-reason: Step 4e is a default output-mode choice, not an artifact-conflict guard; --force on this route would teach users that the flag means "change behavior" rather than "overwrite an artifact."
```

```route-arg
dispatch: (doc compact <path>)
param: name=<path>; required=required; placeholder=<path>; class=type; rule=markdown file path or attachment
```
