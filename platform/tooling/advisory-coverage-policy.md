# Advisory Coverage Policy

Documents the hybrid namespace advisory coverage decision and denylist
extension paths. Policy lists live in
`platform/data/command-advisory-policy.json` and are read by
`platform/tooling/command-advisories.py` at validation time.

## Namespace coverage decision

`platform/data/command-advisory-policy.json` -> `requiredNamespaces` declares
which namespaces must have an advisory file. The required set is `["agent",
"collab", "quality"]`. Advisory files are resolved from two locations:
`platform/data/advisories/<namespace>.json` (central) or
`commands/<namespace>/data/<namespace>.json` (per-slice). The validator
checks both; a namespace needs exactly one to satisfy coverage. Use the
per-slice location when the namespace has its own `commands/<ns>/data/`
directory (e.g. `commands/collab/data/collab.json`).

The following namespaces are explicitly exempt from advisory coverage.
Exemption reasons are authoritative in
`platform/data/command-advisory-policy.json` -> `namespaceCoverageExemptions`:

| Namespace | Advisory file | Decision | Reason |
|---|---|---|---|
| `doc` | none | exempt | Documentation rewrite routes are artifact-specific and intentionally exempt from caller recommendations. |
| `git` | none | exempt | Git workflow routes depend on repository and issue state, so caller recommendations remain policy-exempt. |
| `test` | none | exempt | Test harness dispatch is a maintainer QA surface and remains policy-exempt from caller recommendations. |

To add a namespace to required coverage: add it to `requiredNamespaces`
in `platform/data/command-advisory-policy.json` and create its advisory
at either `platform/data/advisories/<namespace>.json` or
`commands/<namespace>/data/<namespace>.json`, conforming to
`platform/data/command-advisory.schema.json`. Prefer the per-slice
location when the namespace has a `commands/<namespace>/data/` directory.

To add an explicit exemption: add a `"<namespace>": "<reason>"` entry
to `namespaceCoverageExemptions` in `platform/data/command-advisory-policy.json`.

## Model/harness leakage denylist

`platform/data/command-advisory-policy.json` -> `modelOrHarnessLeakageTerms`
lists vocabulary tokens whose presence in advisory content signals a
model- or harness-specific leak. The current set is `["claude",
"codex", "gpt", "haiku", "opus", "sonnet"]`.

To add a new model family token: add the lowercase base name to
`modelOrHarnessLeakageTerms` in `platform/data/command-advisory-policy.json`.

**Extension rule:** Tokens must be lowercase base names (no version
suffixes, no punctuation). The checker normalizes to lowercase before
matching; adding `Claude` or `Claude-3` is redundant — add `claude`
only.
