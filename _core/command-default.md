# Command Default

Surface-wide bare-input policy for command routes. Routes that declare `default=none` on a `required=optional` parameter row cite this file as the governing contract.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** command default policy, bare namespace dispatch, abort-with-contextual-help, empty input policy

## Steps

1. Read this document when implementing bare-input behavior for any route or namespace.
2. Apply the abort-with-contextual-help rule for each input shape in the table below.
3. Do not mutate state from this documentation-only reference.

## Notes

- **Rule:** On bare or incomplete invocation, abort immediately — before any state mutation — and emit contextual help. The abort surface is the discovery surface: it tells the caller exactly what the system expects next.

- **Abort-with-contextual-help table**

  | Input shape | Abort message emits |
  |-------------|---------------------|
  | Bare namespace (no command token) | Route roster for the namespace |
  | Required command choice missing | Allowed value set for the missing command |
  | Required flag missing or `default=none` optional omitted | Flag signature and description |

- **Bare-namespace dispatch policy:** A bare namespace invocation (e.g., `/collab` with no further tokens) must never silently dispatch to any route, mutating or otherwise. It aborts and emits the command roster for that namespace. This prevents exploratory keystrokes from triggering work the caller did not request.

- **Consistency requirement:** All three input shapes follow the same rule. There are no per-route exceptions to abort-on-empty; only the content of the contextual help differs by input shape.

- **Route-arg link:** A `route-arg` parameter row with `default=none` declares that bare omission of that parameter triggers this policy. Routes must not silently dispatch when a required-optional parameter with `default=none` is absent. See [`_core/command-argument.md`](command-argument.md) → **`route-arg` Block Schema**.

- **Scope:** This policy governs mutating and read-only routes equally. Defaulting a bare namespace to a mutating route is higher risk (side effects on exploratory input), but even read-only routes must not silently dispatch from a bare namespace.
