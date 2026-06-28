# agentId vocabulary

Shared vocabulary for the `agentId` value recorded in collab registry `participants[]`.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab agentId, agent identity vocabulary, stable model family tokens

## Steps

1. Read this document before changing init, join, registry schema prose, or helper validation for `agentId`.
2. Use this document as the single source for route prose. Do not duplicate the precedence list in downstream route files.
3. Do not mutate registry state from this documentation-only reference.

## Notes

- **Purpose:** `agentId` is an at-join forensic marker for the active runtime harness. `agentId` is not authentication and is not a model-enforcement mechanism.

- **Precedence:** Declare the first usable value from this list:
  1. Stable model-family token when the harness exposes one: `opus`, `sonnet`, `haiku`, `claude`, `gpt`, `gpt-mini`, `gemini`, or `codex`.
  2. Versioned model identifier when the harness exposes only an exact model string, such as `claude-sonnet-4-6` or `gpt-5.5`.
  3. Harness or surface name when no model identity is available, such as `composer`, `claude-code`, or `codex-cli`.
  4. The literal string `unknown`, exact lowercase, only when the harness exposes no usable identity at all — identity is inaccessible at the harness layer.

- **Format:** Use lowercase, hyphenated tokens. Prefer stable family or surface tokens for new joins. Existing versioned registry values remain historical records and must not be migrated solely to match this vocabulary.

- **Harness-inaccessible identity:** `unknown` is reserved for the harness-inaccessible case only: the harness cannot expose any identity. Free-form alternatives such as `UNKNOWN`, `unspecified`, and `n/a` are rejected by the helper. Do not pass `unknown` when the harness exposes an identity that the caller chooses not to declare — use `caller-declined` instead.

- **Caller-declined identity:** `caller-declined` is the token for explicit opt-out: the harness exposes a usable identity but the caller deliberately chooses not to declare it. `caller-declined` is a distinct state from harness-inaccessible (`unknown`). The helper counts `caller-declined` joins before any rejection enforcement; policy on whether to reject or allow caller-declined identity is determined by the governing collab configuration.

- **Trust model:** The helper enforces presence, whitespace stripping, the exact lowercase `unknown` and `caller-declined` tokens, and invalid unavailable-identity aliases. The helper cannot verify whether the caller chose the highest-precedence available token or whether the harness is genuinely inaccessible.
