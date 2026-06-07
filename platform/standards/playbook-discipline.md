# Playbook discipline

Generic rules for project playbook structure. Project-specific values — per-file section
contracts, forbidden sections, merge gate checks specific to the file set — belong in the
project playbook contract. Generic prose mechanics (em-dash discipline, link-then-italic
first mention, bold-colon run-in labels) are governed by the system framework canon:
`author-voice.md` (voice and typography) and `markdown-workflow.md` (formatting rules).
Cite those files by name and role — do not restate them here.

## Section-contract pattern

A playbook defines required `##` headings for each owned file. Every file contract:

- Lists required `##` headings in the order they must appear.
- Declares when a section opens with a specific label (e.g., `**Queue:**`, `**Steps:**`,
  `**Checks:**`, `**Rules:**`).
- Prohibits extra `##` sections beyond those listed.

## Lean gate

Every sentence must be load-bearing — it answers a question a solo coder or artist would
ask during a planning session. Brevity is not a defect.

## Exactly-four-tasks rule

A `## Next 4 tasks` section requires exactly four numbered items. Done state uses `✅`
after the list number. Do not remove `✅` or mark items undone without explicit direction.

## PHASES ledger coupling

When a `## Phase status ledger` table shape is consumed by a script, the playbook
contract must name that script as the enforcement owner of the table's structure. The
human contract doc is advisory; the script is the enforcement owner. Any edit to the
ledger shape must stay compatible with the named script — update both together.
