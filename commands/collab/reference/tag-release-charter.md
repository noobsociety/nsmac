# Tag & Release — charter restatement

This file restates the durable facts backlog row #20 (Tag & Release) rests on,
in-repo, so the `2026-07-04-tag-release` collab's directive no longer depends
on a `~/Downloads/` citation for its charter facts (show-policy §Provenance).
It also states the release-naming disambiguation requirement the new
`(collab release)` route prose must satisfy.

## Charter facts (restated from row #20, re-synced 2026-07-04)

- **Verdict:** proceed — the one additive-capability item in the v1 backlog
  set; wiring is absent, not the underlying capability.
- **Substrate present:** `commands/collab/engine/git_repo.py` (308 LOC)
  already wraps git operations; `platform/standards/git-convention.md`
  already defines a `release` scope and the `chore(release): merge dev to
  main` title; #16 (git folded into `collab`) is closed, so `tag`/`release`
  sit beside the folded `commit`/`issue` routes rather than in a separate
  namespace.
- **Dependency state:** #16 (consolidation) closed. #17 (polish) is the
  named remaining predecessor as of the audit's last re-sync.
- **Changelog:** the `doc/write-changelog` route was retired with the `doc/`
  namespace in #16 and was **not folded** — no changelog-cut engine remains
  in the tree. Only the `CHANGELOG.md` conventions in
  `platform/standards/document-standard.md` and
  `platform/standards/style-guide.md` survive. Row #20's changelog leg is
  therefore a rebuild decision, not a wiring task; this collab's Action Plan
  assigns that decision to the moderator role.

## Release-naming disambiguation requirement

On first mention in `commands/collab/release/index.md` (and any doc that
references it), disambiguate:

- `release` as the conventional-commit scope defined in
  `platform/standards/git-convention.md` (e.g. `chore(release): merge dev to
  main`), from
- `(collab release)` as the command verb / route name introduced by this
  collab.

This requirement is a read-only dependency for the route-authoring work in
`commands/collab/release/index.md`; the route doc must satisfy it on first
mention.

## Known gap

A `charteredDeliverables` entry for this file's path is a moderator-only,
Audit-phase-scoped declaration and cannot be added by the technical-writer
role once Audit has closed as a one-speak phase. This was flagged to the
moderator role in this collab's Handoff phase, and it exposes a broader
charter-coverage workflow gap: once a deliverable is identified after the
moderator's one-speak Audit block has closed, `charteredDeliverables` cannot
enforce it, even when a later Action Plan item correctly names it. This file
raises the issue for a moderator/system decision; it does not self-charter
new deliverables.

Engine-level options to decide:

- **Late-charter amendment:** add a sanctioned moderator route or seal-time
  mechanism for amending `charteredDeliverables` after Audit when the record
  explicitly reopens or records the amendment provenance.
- **Action-Plan coverage substitute:** define a sanctioned seal-time coverage
  rule that treats checked `[precondition]` / `[execute]` Action Plan items
  plus execution `touchedPaths` as the binding coverage surface when Audit had
  no enforceable `charteredDeliverables` block.

Neither option has been adopted as of this writing; this gap remains open,
not resolved.
