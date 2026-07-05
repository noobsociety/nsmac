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
grep -Fq 'platform/templates/CLAUDE.md' commands/agent/install/index.md || fail "install.md does not require CLAUDE template"
grep -Fq 'platform/templates/AGENTS.md' commands/agent/install/index.md || fail "install.md does not require AGENTS template"
grep -Fq 'platform/templates/REPOSITORY.md' commands/agent/install/index.md || fail "install.md does not require REPOSITORY template"
grep -Fq 'Verify `AGENTS.md`, `CLAUDE.md`, and `REPOSITORY.md` exist in the repo root' commands/agent/upgrade/index.md || fail "upgrade.md does not require installed scaffold"
grep -Fq 'writes only `AGENTS.md`, `CLAUDE.md`, and (when overlap-free) `REPOSITORY.md`' commands/agent/upgrade/index.md || fail "upgrade.md boundary omits scaffold files"

grep -Fq 'a target path of `~/.cursor` is permitted' commands/agent/install/index.md || fail "install.md lacks valid ~/.cursor target policy"
grep -Fq 'a target path of `~/.cursor` is permitted' commands/agent/upgrade/index.md || fail "upgrade.md lacks valid ~/.cursor target policy"
grep -Fq 'A checkout developed in place at `~/.cursor` is a valid target repository root' commands/agent/install/index.md || fail "install.md lacks valid ~/.cursor target policy"
grep -Fq 'A checkout developed in place at `~/.cursor` is a valid target repository root' commands/agent/upgrade/index.md || fail "upgrade.md lacks valid ~/.cursor target policy"
grep -Fq 'git rev-parse --show-toplevel' commands/agent/install/index.md || fail "install.md does not resolve target through git work tree"
grep -Fq 'current working directory may be the repo root or any nested path inside the target git work tree' commands/agent/install/index.md || fail "install.md lacks nested CWD policy"
grep -Fq 'current working directory is not inside a git work tree' commands/agent/install/index.md || fail "install.md lacks non-git CWD abort"
if grep -Fq 'writable directory' commands/agent/install/index.md; then
  fail "install.md still uses writable-directory target contract"
fi

grep -Fq 'TODO(install)' platform/templates/AGENTS.md || fail "AGENTS template lacks TODO(install)"
grep -Fq 'TODO(patch)' platform/templates/REPOSITORY.md || fail "REPOSITORY template lacks TODO(patch)"

if grep -R 'TODO(agent)' commands/agent platform/templates tests/specs/templates.md commands/commands.md >/dev/null; then
  grep -R 'TODO(agent)' commands/agent platform/templates tests/specs/templates.md commands/commands.md >&2
  fail "agent route contract still references TODO(agent)"
fi

grep -Fq 'no installed scaffold file contains unresolved `<!-- TODO(install): ... -->` markers' commands/agent/install/index.md || fail "install.md lacks TODO(install) validation"
grep -Fq 'no `<!-- TODO(patch): ... -->` markers remain' commands/agent/patch/index.md || fail "patch.md lacks TODO(patch) validation"
grep -Fq 'if any `TODO(install)` marker would survive in the candidate patch, **ABORT**' commands/agent/upgrade/index.md || fail "upgrade.md lacks unresolved TODO(install) overwrite abort"

grep -Fq 'include a command path only when that exact path exists in the target repo' commands/agent/patch/index.md || fail "patch.md lacks deterministic validation-command inference"
grep -Fq 'sibling route file' commands/agent/patch/index.md || fail "patch.md lacks sibling-route failed example"

printf 'OK: agent route contract covers run-root and marker-class invariants\n'
