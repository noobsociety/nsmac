# /quality assess web

**WSE** — principal web-software review from the repository tree: structure, boundaries, correctness, safety, maintainability, and tests.

## Trigger

**Slash:** `/quality assess web`
**Signature:** `/quality assess web <project>`
**Prose dispatch:** `(quality assess web <project>)` — prose routing hint; not a terminal command.
**Search phrases:** web stack review, WSE, principal web engineer

## Steps

1. Resolve **`<project>`** from the first argument or `@`-mention per **Invocation** in **Notes**. If missing, **ABORT**: `<project>` is required.
2. Walk **Rubric** items **1–9** in **Notes**; skip what does not apply.
3. When rubric learning applies, follow [quality-learning](../../../core/framework/quality-learning.md) **Protocol** steps 2–6 after the primary review.

## Notes

- **Parameters:** `<project>` — project root path (required); `@`-mentions are additive.
- **Constraint:** Ground claims in files and `@`-mentions; screenshots alone are insufficient.
- **Scope:** **`<project>`** — web stack root; resolve absolute when possible. Web stacks (static, SPA, SSR, BFF, edge, workers, bundlers, UI, CSS, tokens as code). Default **non-game** web. **Phaser/hybrid:** own host shell, DOM outside canvas, routing, build/tooling, server/BFF, auth, CMS, CI glue — not gameplay canvas. Wrapper that mounts Phaser (e.g. `PhaserGame.tsx`): WSE owns wrapper lifecycle, props, events; IGD owns inside `Game`. **In:** structure, API boundaries, validation at edges, async/errors, config/secrets, web-typical security (not pentest), code-level a11y, tokens, tests/CI, observability when present. **Out:** image-only review; pure gameplay canvas with no web slice; repos with no web delivery.
- **Dependencies:** If required context is missing, **ABORT** per **`context-gate.md`**.
- **Invocation:** First token = `<project>`; if absent, ABORT; invalid path → ABORT; multiple positional path args → first wins; multiple `@`-mentions are additive; resolve absolute when possible.
- **Rubric** (walk items 1–9; skip what does not apply):
  - **1 Structure** — acyclic layers when present; single wiring for globals; isolatable features; DDD/ports only if pattern exists.
  - **2 Boundaries** — typed HTTP/RPC; secrets server-side; narrow exports.
  - **3 Types/validation** — no raw JSON through UI/domain without mapping; schemas at boundaries; config drift tests when practiced.
  - **4 Async/errors** — I/O in right layers; cap fan-out; user-facing errors formatted at right layer.
  - **5 Config/secrets** — env validated at bootstrap; no committed secrets; client/server env split.
  - **6 Security** — XSS sinks, auth/session norms, obvious dependency red flags.
  - **7 A11y in code** — focus, labels, errors, live regions; loading/empty/error routes; host modals/nav only. Canvas keyboard focus inside the game is IGD scope.
  - **8 Styling/tokens** — centralize tokens; data-viz color separation in app charts.
  - **9 Tests** — match pyramid repo uses; contract/snapshot/drift when aligned.
  - **Process** — map entrypoints; read root **`OWNERS.md`** if present when boundaries unclear; if `OWNERS.md` is absent and boundaries are unclear, ask `/quality assess operations` to generate it; missing router/CI = note, not automatic failure; **default** one topic per round; **`full`** or user "full pass" → all items with file anchors; prefer incremental fixes. `/quality tune` may aggregate this pass with other principal reviews.
  - **Feedback** — file + boundary; risk→fix; no roadmap unless in scope.

```route-arg
dispatch: (quality assess web <project>)
param: name=<project>; required=required; placeholder=<project>; class=type; rule=web project root path
```
