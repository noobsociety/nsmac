# /quality assess interface

**UID** — principal user-interface review from a screenshot: hierarchy, clarity, consistency, affordances, and visible accessibility with actionable feedback.

## Trigger

**Slash:** `/quality assess interface`
**Signature:** `/quality assess interface <image> <project>`
**Prose dispatch:** `(quality assess interface <image> <project>)` — prose routing hint; not a terminal command.
**Search phrases:** principal UI review, screenshot review, UID

## Steps

1. Resolve **`<image>`** and **`<project>`** per **Parameters** in **Notes**. If either is missing, **ABORT**: list which argument(s) are missing.
2. Apply the **Rubric** in **Notes**; tie every finding to visible evidence.
3. When rubric learning applies, read [quality-learning](../../../core/framework/quality-learning.md) and follow its **Protocol** and **Review workflow** after the primary review.

## Notes

- **Parameters:** `<image>` — screenshot path (required); attachment counts as `<image>`. `<project>` — project root for vocabulary (required). **Resolution:** without attachment: first token = `<image>`, second = `<project>`; with attachment: attachment = `<image>`, first token = `<project>`. ABORT with the name of any missing argument.
- **Constraint:** Stay on visual impact; do not switch to architecture, coding, or stack unless asked.
- **Scope:** **`<image>`** is primary; **`<project>`** only for token or component vocabulary. In scope: layout, type, color/contrast, spacing, surfaces, control states, labels, empty/loading when visible, chrome/modals, chart chrome when shown. **Game/canvas-only with no overlay:** ask for HUD/menu screenshot before rubric items on controls and content-as-UI. Product and platform agnostic. **Out:** implementation, refactors, tests, APIs, performance, security, roadmap.
- **Dependencies:** If required context is missing, **ABORT** per **`context-gate.md`**.
- **Rubric (evidence-backed):** **1 Hierarchy** — scan order, grouping, density, alignment. **2 Typography** — scale, weight, readability, casing. **3 Color** — contrast, semantic color, data-viz vs UI semantics, non-color cues. **4 Surfaces** — elevation, borders, noise. **5 Spacing** — vertical rhythm, sibling rhythm, hit targets. **6 Controls** — affordance, primary/secondary, selection state, focus, disabled/loading. **7 Content-as-UI** — specific labels, errors/help placement, empty states. **8 Data viz** *(skip if no charts)* — plot framing, legend coherence, loading pattern. **Process:** full frame then focal task; prioritize impact; default one issue per round; **`full`** suffix or user asks “full pass” → all findings anchored to region; implementation-neutral first; tokens only with context. **Feedback:** region in plain language; problem→fix; no fake paths; vocabulary order: principle → pattern → optional token names from context only; suggest next screenshot for iteration.

```route-arg
dispatch: (quality assess interface <image> <project>)
param: name=<image>; required=required; placeholder=<image>; class=type; rule=image path or attachment
param: name=<project>; required=required; placeholder=<project>; class=type; rule=project root path
```
