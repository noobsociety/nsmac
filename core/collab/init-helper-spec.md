# Init helper derivation spec

Canonical derivation rules for `tools/collab/registry.py init`. Both the helper implementation and the route interface description in [`init.md`](../../commands/collab/init/index.md) are downstream of this spec. Do not diverge either without updating this doc first.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab init helper spec, init derivation rules, collab init transaction

## Steps

1. Read this document before changing `tools/collab/registry.py init` or [`init.md`](../../commands/collab/init/index.md).
2. Keep the helper implementation, route interface prose, and tests aligned with the derivation rules below.
3. Do not mutate registry state from this documentation-only reference.

## Notes

### Title normalization

Source: the trimmed `<name>` argument - all tokens after `/collab init` with declared helper flags stripped.

Algorithm:

1. Collapse repeated whitespace to a single space.
2. Title-case ordinary words.
3. Preserve known command/product acronyms: `AI`, `API`, `CLI`, `DX`, `QA`, `UI`, and `UX`.
4. Keep small connector words lowercase when they are not the first word.

The normalized result is the registry `title`, transcript H1, and description source.

### Slug derivation

Source: the trimmed `<name>` argument - all tokens after `/collab init` with declared helper flags stripped.

Algorithm:

1. Lowercase the normalized title.
2. Replace every run of non-alphanumeric characters with a single hyphen.
3. Trim any leading or trailing hyphens.

The result is the `slug` field. If the result is empty after trimming, abort with: `slug is empty; ask the moderator for a clearer name`.

### Collab id and transcript path

- `id`: `YYYY-MM-DD-<slug>` where the date is today in local time.
- `transcriptPath`: `records/YYYY-MM-DD-<slug>.md`

### Sequence number

The `sequence` field is the next unused positive integer across all collab entries in registry `collabs`. Compute as `max(existing sequence values) + 1`, or `1` if no entries exist. Sequence values must be unique; abort on collision.

### agentId capture at init

The moderator's `agentId` is captured once at init time, not at first speak. The route must pass the declared helper flag `--agent-id <agentId>`, applying the shared vocabulary and precedence in [agent-id.md](../../core/collab/agent-id.md).

Do not copy `agentId` from role files, prior records, examples, or documentation. Record the at-init value in registry `participants` under the moderator row. No speak-time revalidation.

### Reviewer-flag schema

Flag: `--reviewer <role>` (optional).

When present:

- Validate that `<role>` is a non-empty string of word characters. Abort if missing or invalid.
- Always write the following three fields to the new registry entry, unconditionally:
  - `reviewerRole`: the supplied `<role>` value
  - `reviewerMode`: `"last-in-convergent-phases"`
  - `reviewerOptionalPhases`: `["Discussion"]`
- If the reviewer role is not yet in `participants`, add a transcript **Reviewer** section noting that the role must join via `/collab join --role <role>` before any participant may contribute, and mark it as `(pending)`. Do not abort.

When absent: omit `reviewerRole`, `reviewerMode`, and `reviewerOptionalPhases` from the new entry.

### Strict-flag set

The init helper accepts exactly one required flag and four optional flags:

- Required: `--agent-id <agentId>`
- Optional: `--reviewer <role>`
- Optional: `--participant-verification` (boolean; no value)
- Optional: `--verification-cap <N>` (positive integer; requires `--participant-verification`)
- Optional: `--preview` (boolean; no value)

All other flag-shaped tokens (any token beginning with `--`) must be rejected before any file write with: `unknown flag: <token>`.

`--force` is ineligible for this route per [`command-argument.md`](../../core/framework/command-argument.md) guard class `registry-integrity`. The guards against duplicate records and registry corruption must not be bypassable.

### `--preview` flag schema

Flag: `--preview` (optional, boolean, no value).

When present:

- Accept the flag as a no-value boolean. If a value token follows `--preview` and it is not another declared flag, it is treated as part of `<name>` per normal init token parsing.
- After the registry and transcript transaction succeeds, derive an absolute `file://` URI from the transcript path using `transcript_path.resolve().as_uri()` and invoke `webbrowser.open_new_tab(uri)`.
- On success, emit `OPEN: file://<abs-path>` as an advisory line after the first output line.
- On failure (any exception from `webbrowser.open_new_tab()`), emit `OPEN: failed: <reason>` as an advisory line. Do not alter the exit code, roll back registry or transcript writes, or re-raise the exception.
- Provide a test injection seam (e.g. a module-level open function) so tests can exercise the `--preview` path without launching a real browser.

When absent: skip the browser-open step entirely. Existing non-`--preview` output is byte-for-byte unchanged.

No future flags may be added to the helper CLI without updating this spec first.
