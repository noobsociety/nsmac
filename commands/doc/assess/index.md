# /doc assess

Classify a Markdown document as good, bad, or ugly, then rewrite until it meets the good rubric or stops on missing facts.

## Trigger

**Slash:** `/doc assess`
**Signature:** `/doc assess <path>`
**Prose dispatch:** `(doc assess <path>)` — prose routing hint; not a terminal command.
**Search phrases:** `assess`, `assess document`, `good bad ugly`, `doc-assess`, `assess doc`

## Steps

1. Resolve `<path>` from the first argument or attachment. If missing, **ABORT**: `<path>` is required.
2. If **`markdown-workflow.md`**, **`markdown-workflow.md`**, or **`markdown-workflow.md`** is required and unreadable, **ABORT** per **`context-gate.md`**.
3. Classify per **Notes** (**Classification rubric**). If both bad and ugly signals appear, choose **ugly** when contradictions or harmful misexecution risk exists. Choose **bad** when bad and ugly signals coexist but no contradictions or harmful risk is present.
4. If **bad**, revise toward **good** (not critique-only). If **ugly**, run **Ugly preflight** in **Notes**, then rewrite when resolvable.
5. Re-assess after each rewrite; cap at **three passes**; if still not good, return best revision plus `Missing facts` for blockers.
6. Output in the order defined under **Output contract** in **Notes**.
7. When rubric learning applies, follow [quality-learning](../../../core/framework/quality-learning.md) after the primary rewrite; keep candidates docs-only.

## Notes

- **Parameters:** `<path>` — Markdown file path (required); attachment is equivalent.
- **Scope:** Invocation-gated. One Markdown route. Binary inputs need extracted text; config-like JSON/YAML/TOML only when prose-like or requested—else `Missing facts`.
- **Mode:** Deterministic workflow; compact edits; reuse terminology; no invented facts; reasoning internal.
- **Classification rubric:** **Good** — clear purpose and audience, scannable structure, accurate claims, examples, minimal fluff, consistent style, actionable steps. **Bad** — idea present but unclear; no internal contradictions or harm risk; weak structure, missing context, ambiguous terms, ungrounded claims. **Ugly** — contradictions, conflicting instructions, or guidance likely to cause wrong or harmful action; structure issues may coexist but are not sufficient alone.
- **Ugly preflight:** (1) List contradiction or risk points. (2) Mark resolvable from context or not. (3) If any critical point is unresolved, return `Missing facts` instead of picking a side. (4) Rewrite only after critical items resolve. **Safety:** Flag destructive commands, deletion, credentials, security bypasses; replace with safe alternatives or placeholders; if environment unknown, block and list `Missing facts`.
- **Rewrite checklist:** State purpose in one to two lines; add minimal audience and prerequisites; restructure (summary then detail; headings; short paragraphs; bullets); make actionable (steps, checklists; for **ugly**, one example that disambiguates a failure mode); remove noise; fix contradictions and terminology.
- **Quality gate before stop:** Purpose explicit; audience or explicit “none”; scannable structure; claims grounded in source; concrete next actions; example when ambiguity could cause wrong action (mandatory for ugly); consistent terms; no major harmful ambiguity; no unresolved safety risk.
- **Output contract:** (1) Initial classification `good` | `bad` | `ugly`. (2) If **good:** brief rationale (one to three bullets); micro-edits only if requested. (3) If **bad** or **ugly:** full revised document by default; if capped at three passes, prepend `Note: revision capped at 3 passes.`; patch-style only when user or compliance requires preserving original structure. (4) If blocked: **bad** — best revision with placeholders; **ugly** with unresolved critical issues — minimal safe scaffold plus placeholders; end with `Missing facts:` bullet list of required unknowns only.
- **Brevity:** Compact rationale; spend tokens on the revised document; do not repeat rubric prose in the answer.
- **Learning:** When `quality-learning.md` is in scope, adaptation candidates stay documentation-only; do not promote docs findings into code-QA lanes.

```route-arg
dispatch: (doc assess <path>)
param: name=<path>; required=required; placeholder=<path>; class=type; rule=markdown file path or attachment
```
