# Topology validator contract

`platform/tooling/audit-topology.sh` enforces the public command topology.

The generated commands catalog may link only public namespace and route `index.md` entrypoints. Backing files under `engine/`, `reference/`, and `data/` are internal and must not become dispatchable catalog entries.
