# Source Vocabulary Allowlist

Defines accepted remnants for the retired name. CI validation must confirm tracked files contain no retired-name hit outside these patterns.

## Accepted patterns

1. **`~/.cursor`** — literal path reference only; the runtime install path used as the bootstrap anchor. Accepted when it appears as a file-system path, not when it names a product or tool.

2. **`dotcursor`** — system name in prose only. Accepted in prose text (e.g. "the dotcursor system", "dotcursor namespace"). Not accepted in file-path segments or directory names.

## Validation recipe

Scan tracked files for the retired name, then exclude lines covered by the two accepted patterns:

```
needle='cur''sor'
accepted_system='dot''cur''sor'
git ls-files -z \
  | xargs -0 grep -Ehin "$needle" \
  | grep -vF '~/.cursor' \
  | grep -vEi "\\b${accepted_system}\\b"
```

Output must be empty for validation to pass. Implement as a dedicated check in the repository audit script and run via `./tests/run.sh`.
