# Host integration

Maps the framework's lifecycle attachment points for host-specific wiring.

Hooks are outside the portable layer by design (`platform/standards/framework-boundaries.md`). This document names each attachment point, the route and lifecycle helper that fires it, the registry state readable at that point, and the mutations the hook must not perform.

## Attachment points

| Hook | Route | Trigger event | Readable state | Prohibited mutation |
|------|-------|---------------|----------------|---------------------|
| `post-speak` | `(collab speak)` | `speak-lifecycle-live` — after transcript and registry are updated | `activePhase`, new contribution anchor, `turnOrder`, `expectedRole` | Registry writes; recursive `(collab speak)` invocations; user-scope collab state root mutations |
| `post-seal` | `(collab seal verification)` | `seal-write` — after `verificationSeal` is written | `verificationSeal`, `status`, `activePhase` | Registry writes; seal invalidation; verdict mutation |
| `post-verdict` | `(collab seal verification --outcome <outcome>)` | `record-verdict` — after `verdict` is recorded | `verificationSeal`, `verdict.outcome`, `status`, `activePhase` | Registry writes; seal invalidation; verdict mutation |
| `pre-write` | Any mutating route | `write-guard` — before atomic `registry.json` replacement | `activePhase`, `revision` (write-guard counter), `participants` | Blocking or altering the pending write; registry or transcript mutation from hook context |

## Constraints

- Each hook name is derived from the lifecycle helper or helper call-site that fires it; no hook name is coined independently of a live code path.
- Hooks are boundary notifications, not orchestration primitives. A host hook may read state and dispatch side-effects (notifications, CI triggers, audit logs); it must not route back into the collab command layer or mutate collab state.
- The readable state listed above is the minimum reliable surface at each hook point. Additional registry fields may be present but are not guaranteed stable across framework updates.
- External service and memory integrations that operate at these boundaries are host concerns; see `platform/standards/framework-boundaries.md` for the full out-of-scope list.
