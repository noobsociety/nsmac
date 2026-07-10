# Advisory coverage policy

The hybrid namespace advisory coverage decision and denylist extension paths are documented here. Policy lists live in
`platform/data/command-advisory-policy.json` and are read by
`platform/tooling/command-advisories.py` at validation time.

## Namespace coverage decision

`platform/data/command-advisory-policy.json` -> `requiredNamespaces` declares
which namespaces must have an advisory file. The required set is `["agent",
"collab"]`. Advisory files live in one per-slice location:
`commands/<namespace>/data/<namespace>.json` (e.g.
`commands/collab/data/collab.json`, `commands/agent/data/agent.json`).

The following namespaces are explicitly exempt from advisory coverage.
Exemption reasons are authoritative in
`platform/data/command-advisory-policy.json` -> `namespaceCoverageExemptions`:

| Namespace | Advisory file | Decision | Reason |
|---|---|---|---|
| `help` | none | exempt | Route lookup renders existing playbooks as a thin pass-through; no capability or effort tier applies. |
| `test` | none | exempt | Test harness dispatch is a maintainer QA surface and remains policy-exempt from caller recommendations. |

To add a namespace to required coverage: add it to `requiredNamespaces`
in `platform/data/command-advisory-policy.json` and create its advisory
at `commands/<namespace>/data/<namespace>.json`, conforming to
`platform/data/command-advisory.schema.json`.

To add an explicit exemption: add a `"<namespace>": "<reason>"` entry
to `namespaceCoverageExemptions` in `platform/data/command-advisory-policy.json`.

## Model/harness leakage denylist

`platform/data/command-advisory-policy.json` -> `modelOrHarnessLeakageTerms`
lists vocabulary tokens whose presence in advisory content signals a
model- or harness-specific leak. The current set is `["claude",
"codex", "fable", "gpt", "haiku", "opus", "sol", "sonnet"]`.

To add a new model family token: add the lowercase base name to
`modelOrHarnessLeakageTerms` in `platform/data/command-advisory-policy.json`.

**Extension rule:** Tokens must be lowercase base names (no version
suffixes, no punctuation). The checker normalizes to lowercase before
matching; adding `Claude` or `Claude-3` is redundant — add `claude`
only.
