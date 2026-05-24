#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

grep -Fq 'global runtime root' commands/agent/install/index.md || fail "install.md does not define global runtime root"
grep -Fq 'target repository root' commands/agent/install/index.md || fail "install.md does not define target repository root"
grep -Fq 'global runtime root' commands/agent/upgrade/index.md || fail "upgrade.md does not define global runtime root"
grep -Fq 'target repository root' commands/agent/upgrade/index.md || fail "upgrade.md does not define target repository root"

grep -Fq 'a target path of `~/.cursor` is permitted' commands/agent/install/index.md || fail "install.md lacks valid ~/.cursor target policy"
grep -Fq 'a target path of `~/.cursor` is permitted' commands/agent/upgrade/index.md || fail "upgrade.md lacks valid ~/.cursor target policy"
grep -Fq 'A checkout developed in place at `~/.cursor` is a valid target repository root' commands/agent/install/index.md || fail "install.md lacks valid ~/.cursor target policy"
grep -Fq 'A checkout developed in place at `~/.cursor` is a valid target repository root' commands/agent/upgrade/index.md || fail "upgrade.md lacks valid ~/.cursor target policy"

grep -Fq 'TODO(install)' templates/AGENTS.md || fail "AGENTS template lacks TODO(install)"
grep -Fq 'TODO(patch)' templates/REPOSITORY.md || fail "REPOSITORY template lacks TODO(patch)"

if grep -R 'TODO(agent)' commands/agent templates tests/specs/templates.md commands/commands.md >/dev/null; then
  grep -R 'TODO(agent)' commands/agent templates tests/specs/templates.md commands/commands.md >&2
  fail "agent route contract still references TODO(agent)"
fi

grep -Fq 'no installed scaffold file contains unresolved `<!-- TODO(install): ... -->` markers' commands/agent/install/index.md || fail "install.md lacks TODO(install) validation"
grep -Fq 'no `<!-- TODO(patch): ... -->` markers remain' commands/agent/patch/index.md || fail "patch.md lacks TODO(patch) validation"
grep -Fq 'if any `TODO(install)` marker would survive in the candidate patch, **ABORT**' commands/agent/upgrade/index.md || fail "upgrade.md lacks unresolved TODO(install) overwrite abort"

grep -Fq 'include a command path only when that exact path exists in the target repo' commands/agent/patch/index.md || fail "patch.md lacks deterministic validation-command inference"
grep -Fq 'sibling route file' commands/agent/patch/index.md || fail "patch.md lacks sibling-route failed example"

printf 'OK: agent route contract covers run-root and marker-class invariants\n'
