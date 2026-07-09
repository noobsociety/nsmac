# Tag Charter Reference

This reference keeps the durable tag-route charter facts in tracked source and records the naming boundary between `(collab tag)` and the conventional-commit `release` scope.

## Charter facts

- **Capability state:** `(collab tag)` is present. It wires dry-run previews, local annotated tag creation, and optional tag push behind an explicit confirmation gate.
- **Substrate present:** `commands/collab/engine/git_repo.py` (308 LOC)
  already wraps git operations; `platform/standards/git-convention.md`
  already defines a `release` scope and the `chore(release): merge dev to
  main` title; `tag` sits beside `commit` and `issue` inside the `collab`
  namespace rather than in a separate namespace.
- **Changelog:** the `doc/write-changelog` route was retired with the `doc/`
  namespace in #16 and was **not folded** — no changelog-cut engine remains
  in the tree. Only the `CHANGELOG.md` conventions in
  `platform/standards/document-standard.md` and
  `platform/standards/style-guide.md` survive. Changelog automation is a
  rebuild decision, not a wiring task.

## Release-Naming Disambiguation Requirement

Any doc that references release naming must disambiguate:

- `release` as the conventional-commit scope defined in
  `platform/standards/git-convention.md` (e.g. `chore(release): merge dev to
  main`), from
- `(collab tag)` as the collab command that creates or previews a git tag.

This requirement is a read-only dependency for tag-route documentation.

## Open system decision

`charteredDeliverables` is a moderator-owned Audit-phase declaration; the
seal-time coverage gate cannot enforce a deliverable the Audit block did not
declare. That workflow gap awaits a moderator/system decision. Until a
code-level policy decision lands (with synchronized updates to
`invariants.md`, `verification.md`, and this reference), narrative docs must
continue to describe the current behavior as "Audit-only charter coverage",
and this file does not self-charter new deliverables.
