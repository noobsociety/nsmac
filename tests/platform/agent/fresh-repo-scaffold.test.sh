#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

tmp="$(mktemp -d "${TMPDIR:-/tmp}/agent-scaffold-outside.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

resolve_install_markers() {
  local repo_name="$1"
  local file="$2"

  REPO_NAME="$repo_name" perl -0pi -e 's/^# Agent guide\n(<!-- scaffolded-at: [^\n]+ -->\n)<!-- TODO\(install\): Replace the heading above with the project-specific title, e\.g\. "Agent guide .*?" -->\n/# Agent guide — $ENV{REPO_NAME}\n$1/s' "$file"
}

extract_markdown_links() {
  local file="$1"

  perl -nE 'while (/\[[^\]]+\]\(([^)]+)\)/g) { say $1 }' "$file"
}

git -C "$tmp" init -q
repo_root="$(git -C "$tmp" rev-parse --show-toplevel)"
repo_name="$(basename "$repo_root")"

for scaffold in CLAUDE.md AGENTS.md GEMINI.md REPOSITORY.md; do
  cp "platform/templates/$scaffold" "$repo_root/$scaffold"
done
resolve_install_markers "$repo_name" "$repo_root/AGENTS.md"

for scaffold in CLAUDE.md AGENTS.md GEMINI.md REPOSITORY.md; do
  [[ -f "$repo_root/$scaffold" ]] || fail "missing installed scaffold $scaffold"
done

grep -Fq '[AGENTS.md](AGENTS.md)' "$repo_root/CLAUDE.md" || fail "CLAUDE.md does not route to AGENTS.md"
grep -Fq '[AGENTS.md](AGENTS.md)' "$repo_root/GEMINI.md" || fail "GEMINI.md does not route to AGENTS.md"
grep -Fq '~/.cursor/commands/commands.md' "$repo_root/AGENTS.md" || fail "AGENTS.md does not reference command catalog"
grep -Fq 'To invoke a global command, resolve any routing-only dispatch hint' "$repo_root/AGENTS.md" || fail "AGENTS.md lacks canonical dispatch sentence"
grep -Eq '<!-- scaffolded-at: [0-9]{4}-[0-9]{2}-[0-9]{2} -->' "$repo_root/AGENTS.md" || fail "AGENTS.md lacks scaffold marker"
if grep -R 'TODO(install)' "$repo_root/CLAUDE.md" "$repo_root/AGENTS.md" "$repo_root/GEMINI.md" "$repo_root/REPOSITORY.md" >/dev/null; then
  fail "installed scaffold contains unresolved TODO(install)"
fi
grep -Fq 'TODO(patch)' "$repo_root/REPOSITORY.md" || fail "REPOSITORY.md lacks TODO(patch)"

while IFS= read -r link; do
  case "$link" in
    ~*|http*) continue ;;
    \#*) continue ;;
  esac
  clean="${link%%#*}"
  [[ -e "$repo_root/$clean" ]] || fail "installed AGENTS.md link does not resolve: $link"
done < <(extract_markdown_links "$repo_root/AGENTS.md")

candidate_dir="$tmp/candidate"
mkdir "$candidate_dir"
for scaffold in CLAUDE.md AGENTS.md GEMINI.md REPOSITORY.md; do
  cp "platform/templates/$scaffold" "$candidate_dir/$scaffold"
done
resolve_install_markers "$repo_name" "$candidate_dir/AGENTS.md"

for scaffold in CLAUDE.md AGENTS.md GEMINI.md REPOSITORY.md; do
  cmp -s "$repo_root/$scaffold" "$candidate_dir/$scaffold" || fail "fresh install differs from resolved upgrade candidate: $scaffold"
done

grep -Fq 'no repo-specific validation commands are currently defined' commands/agent/patch/index.md || fail "patch route does not define fresh-repo validation fallback prose"
if grep -Fq 'leave a bounded `<!-- TODO(patch): list repo-specific validation commands -->` placeholder' commands/agent/patch/index.md; then
  fail "patch route still preserves a TODO(patch) validation placeholder"
fi

printf 'OK: fresh repo scaffold install and upgrade candidate are valid\n'
