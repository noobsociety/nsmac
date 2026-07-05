# Workflow Model

How collab records close.

## Trigger

**Slash:** (reference only - not an invocable route)
**Prose dispatch:** (reference only - not an invocable route)
**Search phrases:** workflow model, reviewer seal, verification seal, close gate

## Current Model

Collabs use one close model:

1. Every non-moderator assigned role has a completed `execution` entry.
2. For reviewer-backed collabs, all assigned participant-verification passes complete.
3. A current, non-stale `verificationSeal` exists, written by `(collab seal verification)`.
4. The reviewer records a `verdict` with `outcome == success`.

Non-reviewer-backed collabs can close after execution completes. Reviewer-backed collabs always require the seal plus a success verdict.

## Completion Lifecycle

`Completion` has two structured substates for reviewer-backed collabs:

- `Completion.execution` - assigned roles run Action Plan items and record execution metadata.
- `Completion.verification` - participant verification runs, then the reviewer writes the seal and records the verdict.

Within `Completion.verification`, `verification.subState` progresses through `participant`, `seal`, and `assessment`.

## See Also

- [verification.md](verification.md)
- [registry.md](registry.md)
- [(collab seal verification)](../seal-verification/index.md)
