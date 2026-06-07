# Git convention

Git convention defines commit subjects, issue metadata, branch names, and
repo-grounded planning rules.

## When the policy applies

Apply this policy whenever an agent generates commit subjects, issue fields, PR
fields, branch names, or repo-grounded implementation plans.

## Issue type and scope sets

Use exactly one type: `ci`, `feat`, `fix`, `chore`, `docs`, `refactor`, `style`,
`perf`, or `test`.
Use exactly one scope: `client`, `server`, `types`, `repo`, `config`, or
`release`.

Use `feature` labels for `feat` work when the visible label inventory supports
that label.
Use `bug` labels for `fix` work when the visible label inventory supports that
label.
Do not invent labels that are not visible in the active repository context.

## Pull requests

Use `Closes #<n>` for `feat`.
Use `Fixes #<n>` for `fix`.
Use `Resolves #<n>` for `chore`, `refactor`, `docs`, `style`, `perf`, and
`test`.

Use `chore(release): merge dev to main` for dev-to-main release pull requests.

## Branches

Create issue branches from `dev` using:

```text
<type>-<scope>/<n>-<issue-title-kebab-case>
```

Strip punctuation from the issue title before kebab-casing.
Collapse repeated hyphens.

## Repo grounding

Scan stack, structure, conventions, `README`, and sources relevant to the
current workspace before deriving metadata or plans.
Read `package.json` when present for dependencies and scripts.
Reference only artifacts that were read in-session, command output that was
run in-session, or facts the user stated.
Never infer file contents or behavior from names or directory layout alone.
Follow [context-gate](context-gate.md) when required evidence is unreadable.

## Commit output

Output only compliant Conventional Commit subject lines unless an explicit
squash workflow requires a multi-line commit message.
Use `type(scope): description`.
Keep type and scope lowercase.
Start the description lowercase.
Keep the subject at or under 72 characters.
Use one logical change per commit.

## References

- [context-gate](context-gate.md)
- [style-guide](style-guide.md)
- [document-standard](document-standard.md)
- [context-management](context-management.md)
