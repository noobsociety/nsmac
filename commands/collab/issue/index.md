# (collab issue)

Prefill a tracked issue workflow (**`create`**) or run implementation work (**`implement`**); both the subcommand and the goal are required.

## Trigger

**Dispatch:** `(collab issue <create | implement> <goal>)` — routing-only command form; not a shell command.
**Search phrases:** `create issue`, `new issue`, `implement issue`

## Steps

1. Resolve `<create | implement>` from the first keyword. If missing, **ABORT**: `<create | implement>` is required.
2. Resolve `<goal>` from remaining tokens after the mode keyword. If missing, **ABORT**: `<goal>` is required.
3. Load [git-convention](../../../platform/standards/git-convention.md) before generating branch names, commit subjects, PR fields, or grounded plans. If not readable, **ABORT** per **`context-gate.md`**.
4. Load [markdown-workflow](../../../platform/standards/markdown-workflow.md) when `<goal>` names devblog paths (`**/devblog/**/*.md`) or lean contracts under `doc/playbook/`. If required and not readable, **ABORT**.
5. For **create**, output **all four** phases in **Notes** (Phases 1-4) with `<goal>` populating issue title, branch name, and PR title. Use **`#<n>`** only for the GitHub issue number of the issue being prefilled (same `<n>` in branch, `Resolves #<n>`, and related fields). Do not run code or edit files.
6. For **implement**, scan the repo per [git-convention](../../../platform/standards/git-convention.md) **Repo grounding** before changing files. Derive `type`, `scope`, and `title kebab-case` from `<goal>`; read `stack` from manifests; populate `requirements` and `constraints` only from what is explicitly stated in `<goal>` or directly readable in the repo — do not infer. Fill **Structured input** in **Notes**, then plan, edit files, and list atomic commit subjects. Run `git` commands only when explicitly requested.

## Notes

- **Route (create vs implement).** `create` -> step 5 only; outputs **Create — Phases 1-4** in **Notes** (create issue, implement issue, branch into `dev`, dev into `main`) — no files edited. `implement` -> step 6; grounds in repo, edits files, and lists atomic commit subjects.
- **Parameters:** `<create | implement>` — mode keyword (required): `create` prefills issue template only; `implement` writes code and edits files. `<goal>` — brief description of the issue or work (required).
- **Scope:** Devblog- and playbook-specific bullets apply only when those paths exist and matching project rules load; otherwise omit them.
- **Conventions:** Types, scopes, branch pattern `<type>-<scope>/<n>-<issue-title-kebab-case>`, PR keywords, and release title `chore(release): merge dev to main` follow [git-convention](../../../platform/standards/git-convention.md).
- **Output contract:** `create` always labels its result as either `Issue delivery: prefill` or `Issue delivery: connector-backed`. `prefill` means the route emitted copy-ready issue and PR fields only. `connector-backed` means the route created the issue through an available tracker connector and must include the created issue URL and number before Phase 2 fields. Callers must branch on this delivery label, not on prose.
- **Owner metadata:** When the caller supplies an owner role, assignee login, or Action Plan role label, preserve it in the Phase 1 metadata block as `Owner:`. Map `Owner:` to `Assignees:` only when a concrete tracker login is directly readable from input or repository metadata; otherwise leave `Assignees:` blank and keep `Owner:` for downstream routing.
- **`_requires:` preservation:** If `<goal>` or caller context contains `_requires: #N` or `_requires: #N #M`, copy the exact `_requires:` line into the create handoff block and the implement structured input. Do not translate these numbers to issue IDs; they are source Action Plan item references.
- **Implement handoff shape:** `implement` accepts the create handoff block as structured input. The block shape is title, optional `Issue: #<n>`, optional `Owner: <role-or-login>`, optional `_requires: #N...`, then `requirements:` with checklist-derived bullets. Preserve all present fields in the grounded implementation plan before editing files.
- **Issue labels (inventory):** For **`Labels:`** in **Create — Phase 1**, use comma-separated names that are directly readable from the active repo context: existing issue or PR templates, repo docs, local metadata, or user-provided label inventory. Match spelling, casing, and spaces exactly. Use the issue-label rule of thumb in [git-convention](../../../platform/standards/git-convention.md) only when those label names are visible in context. If no label inventory is directly readable, leave `Labels:` empty and say why. Do not invent labels. Do not require a network lookup.
- **Acceptance criteria:** Use three to five `- [ ]` lines; text after each marker stays <= 80 characters.
- **Headings for `create` output:** Use these `###` titles **above** each block (never inside paste fences): **Phase 1 — Create issue**, **Phase 2 — Implement issue**, **Phase 3 — branch into `dev`**, **Phase 4 — dev into main**. They pair with **Create — Phase 1-4** bullets below.
- **Create — Phase 1 (create issue):** Emit **`### Phase 1 — Create issue`** above the fence (never inside it). Paste block: plain `Assignees` / `Labels` / `Milestone` / `Projects` lines, one per line (omit `Assignees` when the tracker does not use it). After each colon, either leave the value empty or set a concrete name — no filler placeholder text in template output. For `Labels:`, follow **Issue labels (inventory)** above (repository `/labels` page, not guessed names).

```text
<issue title>

Issue delivery: prefill
Owner: <owner>
Assignees: <assignee>
Labels: <label>
Milestone: <milestone>
Projects: <project>

## Acceptance criteria
- [ ] <criteria>
```

- **Create — Phase 2 (implement issue):** Branch and **Subject** per [git-convention](../../../platform/standards/git-convention.md). Emit **`### Phase 2 — Implement issue`**, then **Field | Value**:

| Field   | Value                                      |
| ------- | ------------------------------------------ |
| Branch  | `<type>-<scope>/<n>-<issue-title-kebab-case>` |
| Subject | `<type>(<scope>): <subject>`              |

- **Handoff:**

```text
(collab issue implement)

<issue title>

Issue: #<n>
Owner: <owner>
_requires: #<action-plan-item>
requirements:
- <criteria>
```

- **Create — Phase 3 (branch into dev):** Heading, then **Field | Value** (PR into `dev`):

```markdown
### Phase 3 — branch into `dev`
```

| Field    | Value |
| -------- | ----- |
| Base     | `dev` |
| Compare  | `<type>-<scope>/<n>-<issue-title-kebab-case>` |
| PR title | `type(scope): <Issue title>` |
| PR body  | `<keyword> #<n>` — keyword from **PR keyword mapping** in [git-convention](../../../platform/standards/git-convention.md) (`feat` -> `Closes`, `fix` -> `Fixes`, all others -> `Resolves`) |

- **Create — Phase 4 (dev into main):** Heading, then dev-to-main sync blocks, then **Field | Value** (release PR):

```markdown
### Phase 4 — dev into main
```

**Before dev-to-main merge** (when `repo:sync-dev` exists in `package.json`)**:**

```shell
npm run repo:sync-dev
```

**After dev-to-main merge** (when `repo:sync-main` exists in `package.json`)**:**

```shell
npm run repo:sync-main
```

| Field   | Value                               |
| ------- | ----------------------------------- |
| Base    | `main`                              |
| Compare | `dev`                               |
| Title   | `chore(release): merge dev to main` |

- **Implement — Structured input:**

```text
<persona>
{{seniority}} {{persona-role}}: {{stack}}.
Files <=300 lines · functions <=80 · max 3 params · branch from dev · atomic commits.
</persona>

<context>
Stack {{stack}} · branch {{type}}-{{scope}}/{{n}}-{{issue-title-kebab-case}}
Commits per git-conventionrule file · PR {{type}}({{scope}}): {{title}}
Owner {{owner}} · Requires {{requires}}
</context>

<task>
{{role}}: goal is {{want}}; outcome is {{benefit}}.
Type {{type}} · Issue #{{n}}: {{title}} · Scope {{scope}} · Goal: {{goal}}
{{requires}}
</task>

<requirements>{{requirements}}</requirements>

<constraints>
No scope beyond acceptance criteria · no new deps without flagging · typing ({{rule}}) · architecture ({{constraint}})
</constraints>

<output>
1. Plan: numbered steps, no code
2. Files: path new | modify | delete
3. Code: one file at a time, fenced
4. Commits: atomic subjects per git-conventionrule file; git only when explicitly requested
5. Checklist: criteria · branch · Phase 3 PR to `dev` · Phase 4 release to `main`
</output>
```

- Default placeholders: `{{persona-role}}` from repo documentation (for example `AGENTS.md`) when directly readable; `{{stack}}` from manifests and sources. Do not default `{{seniority}}` — omit the token if the user did not supply it. Leave any placeholder not directly readable as a literal; do not guess.
- **Git discipline:** One commit per acceptance criterion or small logical unit; keep the branch buildable.

```route-arg
dispatch: (collab issue <create | implement> <goal>)
param: name=<create | implement>; required=required; placeholder=<create | implement>; class=literal; values=create | implement
param: name=<goal>; required=required; placeholder=<goal>; class=type; rule=free text issue goal
```
