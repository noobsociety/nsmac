# Planned-Routes Gate

Reference for `commands/collab/engine/planned_routes.py`.

## Trigger

**Slash:** (reference only - not an invocable route)
**Prose dispatch:** (reference only - not an invocable route)
**Search phrases:** planned routes, planned route gate, validate_planned_route_prerequisites

## Steps

1. Read this document when auditing or changing `commands/collab/engine/planned_routes.py`.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

`validate_planned_route_prerequisites(config_root: Path) -> None` is retained as a load-time hook for future route gates. It currently performs no checks because no planned route is active.

A future planned route is any route that would change the committed workflow model or add a new close gate. Before such a route becomes selectable, the same change must add the route documentation, helper contract, registry/schema notes, and tests that prove the new path end to end.

## Current Gate Status

No planned-route prerequisite gate is active. The current workflow model is documented in [workflow-models.md](workflow-models.md).
