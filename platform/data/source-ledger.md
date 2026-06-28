# Source ledger

Disposition record for retired source carriers and embedded metadata blocks. Rows are added only for active retirement work; completed carrier history is represented by the executable checks that now own the invariant.

The carrier-inventory half of `platform/tooling/check-source-ledger.py --check`
is dormant-by-design while this table has zero rows: this repo currently has no
active retired source carriers to declare. The schema and retired-trace scan
remain active on every audit run. If a future migration introduces a live
carrier row, inventory validation activates automatically and every discovered
carrier must have a ledger row.

| Source path | Normative essence | Destination owner | Load contract | Validation check | Delete condition |
|---|---|---|---|---|---|
