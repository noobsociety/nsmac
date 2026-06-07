# Markdown workflow

Markdown workflow defines default formatting, precedence, and table of contents
behavior for authored Markdown surfaces.

## When the policy applies

Apply this policy when authoring or editing Markdown-shaped content unless a
more specific route or project contract overrides it.

## Precedence

Use this order from highest to lowest priority:

1. Devblog weekly structure for `devblog` weekly entries.
2. Devblog general contract for other personal-account prose.
3. Lean playbook contracts under `doc/playbook`.
4. Invocation-gated workflow directives while the workflow is active.
5. General Markdown defaults from [style-guide](style-guide.md).

Narrower path scope wins over generic scope.
Active invocation wins over passive path matching.
Shared helper policies provide constraints and references only.
[context-gate](context-gate.md) wins whenever an edit depends on unreadable
context.

## Table of contents

Do not add a table of contents from heading count alone.
Add or refresh a table of contents only when the user asks, a playbook requires
one, or an existing file already has a table of contents block.

Use `**Table of contents**` as the label.
Place the label after the opening summary and before the first substantive
section.
Use unordered Markdown links to same-document anchors.
Keep link text plain.
Strip punctuation from generated anchors.
Collapse repeated hyphens in generated anchors.
Use collision suffixes in first-occurrence order.

When a table of contents is explicitly needed for a single-heading document,
emit the label and omit the list.

## References

- [style-guide](style-guide.md)
- [document-standard](document-standard.md)
- [context-management](context-management.md)
- [author-voice](author-voice.md)
- [context-gate](context-gate.md)
