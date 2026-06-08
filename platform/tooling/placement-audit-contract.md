# Placement audit contract

`platform/tooling/audit-placement.sh` enforces the vertical-slice layout.

It fails when retired root directories (`core/`, `tools/`, `templates/`, or `data/`) remain, when a Python file under `commands/<ns>/` imports another `commands/<other-ns>/` slice, or when a Markdown file under `commands/<ns>/` links to another command slice. Imports inside one slice, including bare sibling imports inside `commands/collab/engine/`, are allowed.
