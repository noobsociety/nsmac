# /quality assess operations

**OPS** — build and operations review: scripts, tooling contracts, CI/deploy when present, and surfaces other principal roles skip.

## Trigger

**Slash:** `/quality assess operations`
**Signature:** `/quality assess operations <project>`
**Prose dispatch:** `(quality assess operations <project>)` — prose routing hint; not a terminal command.
**Search phrases:** build review, CI review, OPS

## Steps

1. Resolve **`<project>`** from the first argument or `@`-mention per **Invocation** in **Notes**. If missing, **ABORT**: `<project>` is required.
2. Walk **Rubric** in **Notes** in order. Skip item **6** if no CI/deploy config exists.
3. When rubric learning applies, follow [quality-learning](../../_core/quality-learning.md) **Protocol** steps 2–6 after the primary review.

## Notes

- **Parameters:** `<project>` — project root path (required); `@`-mentions are additive.
- **Scope — ownership:** WSE — app shell, routing, test setup; IGD — scenes, loop, preload keys, gameplay; UID — screenshots; OPS — the rest including ambiguous files (name overlap, ask user).
- **Scope — primary:** `tools/` (for example docs, public, assets subdomains when present), Vite prod/dev configs affecting output paths, root scripts, `requirements.txt`, CI/deploy, contributor prerequisites.
- **Scope — out:** no direct audit of app shell, game scenes, or screenshot-only UI — cite downstream impact only.
- **Dependencies:** If required context is missing, **ABORT** per **`context-gate.md`**.
- **Invocation:** First token = `<project>`; if absent, ABORT; invalid → ABORT; multiple → first; resolve absolute when possible. Read `tools/`, `requirements.txt`, `vite/config.dev.mjs`, `vite/config.prod.mjs`, root scripts, CI paths, `@`-mentions; state unreadable files explicitly.
- **Rubric** (walk in order; skip item **6** when no CI/deploy config exists):
  - **1 Runability** — documented prerequisites, entry points, usage on failure, platform assumptions; manifest vs import drift.
  - **2 Exit codes** — non-zero on failure; atomic writes; stderr vs stdout.
  - **3 Idempotency** — re-run safe; destructive steps explicit; stateful intermediates documented.
  - **4 Inter-script contracts** — path and format contracts; documented ordering.
  - **5 Lifecycle** — referenced vs orphan scripts; empty dirs → delete or `.gitkeep`+comment; scope creep into `src/`; names match behavior.
  - **6 CI/deploy** — triggers, secrets, deploy atomicity, parity with local scripts.
- **Process:** Map build dirs, bundler configs, manifests, README script accuracy. Read **`OWNERS.md`** first if present. Per script: note prereqs, contract, failure, idempotency, consumers. Default one issue per round; **`full`** or "full pass" → all anchored findings; targeted fixes over rewrites. **OWNERS.md:** if missing and boundaries unclear, offer a root table (globs → role + rationale) from actual tree only; save at repo root and tell user to commit.
- **Feedback:** Script paths; risk→fix; cross-role impact named without auditing their code; end with what was checked and next risk.

```route-arg
dispatch: (quality assess operations <project>)
param: name=<project>; required=required; placeholder=<project>; class=type; rule=project root path
```
