# /quality assess game

**IGD** — principal game-engineering review for browser-delivered games (Phaser-native when present): scenes, loop, domains, assets, input, physics, audio, canvas performance, ship path.

## Trigger

**Slash:** `/quality assess game`
**Signature:** `/quality assess game <project>`
**Prose dispatch:** `(quality assess game <project>)` — prose routing hint; not a terminal command.
**Search phrases:** game code review, Phaser review, IGD

## Steps

1. Resolve **`<project>`** from the first argument or `@`-mention per **Invocation** in **Notes**. If missing, **ABORT**: `<project>` is required.
2. Walk **Rubric** items **1–10** in **Notes**; skip or generalize Phaser-only checks when Phaser is absent.
3. When rubric learning applies, follow [quality-learning](../../../core/framework/quality-learning.md) **Protocol** steps 2–6 after the primary review.

## Notes

- **Parameters:** `<project>` — game project root path (required).
- **Scope:** **`<project>`** — game root; resolve absolute when possible. Phaser 3: game root, `GameConfig`, scenes, loaders. **Packaged WebView:** in scope when play is HTML/JS/WebGL bundle. **Phaser absent:** still review loop, assets, input, rendering, perf, ship; skip Phaser jargon without evidence. **In:** gameplay, in-engine UI, canvas loop, loaders/tilemaps, physics/audio pipelines. **Out:** host SPA, routing, marketing/auth/CMS, SSR, CI/doc except canvas glue. **Exclude:** headless-only or native-only with no play loop.
- **Dependencies:** If required context is missing, **ABORT** per **`context-gate.md`**.
- **Invocation:** First token = `<project>`; if absent, ABORT; invalid → ABORT; multiple → first; resolve absolute when possible.
- **Rubric:** **1 Entry/scenes** — `GameConfig`, scene order intentional; thin bootstrap. **2 Orchestration** — scenes delegate; no leaks. **3 Domains** — barrels, acyclic graph, kernel vs logic. **4 Assets** — keys match files; Tiled alignment; atlas build scripts before orphan flags. **5 Input/camera** — world/screen vs camera; gameplay-first framing. **6 Time/physics** — fixed timestep; coherent collision/depth. **7 Feedback** — audio/VFX/in-engine UI; keyboard focus inside Phaser overlays is IGD scope. Host chrome is WSE scope. **8 Performance** — canvas memory/draw/stutter; pool hot paths. **9 Loop/ship** — repeatable play-test path load→action→feedback→outcome; hollow menus flagged. **10 Phaser↔host** *(skip if Phaser is absent)* — typed boundary; no host framework imports in game; hybrid wrapper: IGD inside `Game`, WSE on wrapper interface only. **Process:** map game root; missing expected assets = state explicitly; read **`OWNERS.md`** if present; if `OWNERS.md` is absent and boundaries are unclear, ask `/quality assess operations` to generate it; **default** one highest-leverage issue; **`full`** or "full pass" → all items with anchors. `/quality tune` may aggregate this pass with other principal reviews. **Feedback:** scenes/domains/doc; ship risk→concrete step; honest scope.

```route-arg
dispatch: (quality assess game <project>)
param: name=<project>; required=required; placeholder=<project>; class=type; rule=game project root path
```
