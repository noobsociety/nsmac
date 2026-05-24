# /doc write readme

Create or update `README*` and `readme*` files using verified workspace facts, `markdown-workflow.md`, `markdown-workflow.md`, and `markdown-workflow.md` (README tone and repository layout tree defer to this command on those paths).

## Trigger

**Slash:** `/doc write readme`
**Signature:** `/doc write readme`
**Prose dispatch:** `(doc write readme)` — prose routing hint; not a terminal command.
**Search phrases:** `update readme`, `create readme`, `readme-write`

## Steps

1. Confirm target path(s) match **`**/README*`** and **`**/readme*`**. If multiple match and the user did not name one, **ask once**. Treat each README as independent unless the user scopes a monorepo package.
2. If **`markdown-workflow.md`**, **`markdown-workflow.md`**, or **`markdown-workflow.md`** is missing from context when needed, **ABORT** per **`context-gate.md`**.
3. Choose **Create** (no file or new package readme) or **Update** (file exists). Default **Update** when unsure; preserve structure unless the user wants a rewrite.
4. Discover in order for orientation (not precedence when facts conflict):
   - **`package.json`** or equivalent if present
   - runnable entry files and obvious **`src/`** roots
   - configs the app loads
   - **`.github/workflows/*`** or equivalent CI
   - **`Makefile`**, **`justfile`**, or similar ops entrypoints
   - the target README last

   When install behavior lives in ops scripts, prioritize those after or instead of manifest-only hints. Cap first-pass reads at six files or two directory levels unless the user names a subsystem; **ask once** when monorepo boundaries stay unclear.
5. When sources disagree on how to run the product, trust runnable code and scripts people use, then CI for the same artifact, then manifest metadata if it matches, then prior README prose last for behavior claims.
6. Include only sections the workspace verifies. Baseline sections:

   - name
   - description
   - optional badges and visuals
   - installation or setup
   - usage
   - support
   - roadmap
   - contributing
   - license
   - status

   Do not add empty headings.
7. **Always include:** **Title (H1)**; **Brief description** (≤80 characters if one line; two short sentences allowed; no “this repo” / “here” except the narrow symlink-first config exception below; move mechanics to **Install** / **Setup** / **Usage**); **Install** or **Setup** (prefer **Install**; use **Setup** when there is no install step); **Usage**; **Status** (see **Notes**).

   **Include when verified:** **Badges** when CI/CD config exists; **Screenshot or Demo** when a reader-visible UI exists and an asset or URL is verified; **Structure** or **Repository layout** when a short map helps; **Prerequisites** when non-obvious; **Configuration**, **Scripts or Commands**, **Deployment**, **Known issues**, **Roadmap**, **Contributing**, **License**, **Support**, **Asset credits**, **Architecture/Conventions** only with evidence.
8. **Repository layout tree:** At each level list subdirectories first (A–Z), then files (A–Z); ASCII order so dot-prefixed entries sort before letters; recurse the same rule; keep optional trailing `#` comments concrete.
9. **Manual TOC:** Required for the repository root **`README.md`** in this workspace. Wrap the TOC block with `---` immediately before the `**Table of contents**` label and immediately after the final TOC entry. For other README paths, the TOC is optional unless requested or already present. When a TOC is present, follow **`markdown-workflow.md`**: list every `##`, `###`, and deeper subsection in order (or label-only when no such headings).
10. **Changelog:** Do not create or edit **`CHANGELOG.md`** (or other changelog paths) unless the user or same task explicitly includes them—then use **`/doc write changelog`**.
11. **MANUAL:** Do not create or edit repo-root **`MANUAL.md`** unless the repo has **Automated setup** (a root shell installer or **`Makefile`/`justfile`** targets clearly used for install/bootstrap) **and** the user or task explicitly includes **`MANUAL.md`**. Otherwise treat **`MANUAL.md`** as out of scope here; use **`/doc write manual`** in a separate invocation when needed.
12. **Symlink-first config repos:** When the main deliverable is config installed into **`~`** or editor dirs via a named installer, the opening line may name platforms, what is managed, and the installer plus symlink targets in one short sentence within the ≤80-character cap even if **Install** repeats the script; **“here”** is allowed only in that narrow case.
13. **Tone:** Present tense; second person or neutral for body; sentence-case headings; short sentences; lists for steps; language-tagged fences; placeholders explicit; plain Markdown without extra decorative rules; emoji only if the project already uses them.
14. **Environment variables and paths** in README body use single backticks, not bold-wrapped code.
15. Before finishing, verify each of the following. Required sections are present and the brief-description limit is met. **Install**/**Setup** and **Usage** are concrete or honestly delegated. **Status** matches the chosen shape and date rule in **Notes**. No commands are invented. Badges appear only when CI config exists. The screenshot rule is satisfied or honestly omitted. The repository root **`README.md`** has a synced TOC wrapped with `---`; TOCs in other README files are synced when present. **Description standards**, **`markdown-workflow.md`**, and **`markdown-workflow.md`** are respected.

## Notes

### Description standards

- **Package registry summary:** Prefer 50-100 characters when package metadata is in scope.
- **README opening paragraph:** Prefer one sentence; use two short sentences only when needed.
- **GitHub repository description:** GitHub allows 350 characters, but prefer fewer than 120.
- **Avoid:** long mission statements, implementation details, setup instructions, and marketing fluff.

- **Merging with `document-standard.md` (Readme):** The [document standard](../../../core/framework/document-standard.md) Readme skeleton maps to this route as: *What the project does* → **Overview**; *Further reading* → **Links**. Add badge, screenshot, and `**Table of contents**` lead-in before the first `##` when verified. In the repository root **`README.md`**, the TOC is required and must be wrapped with `---` before and after the TOC block. Full section order (omit any block you do not need, do not reorder blocks you keep): brief and optional badge; **optional** verified screenshot or other image right after the opening line and before the first `##` or *Table of contents*; required root README `**Table of contents**` listing every `##` in order; then **Overview** → **Setup** → **Usage** → **Structure** → **Links** → **Status** (always last).
- **Status — default shape:**

```markdown
## Status

> Last updated: YYYY-MM-DD

What works now and what is in progress (two sentences max).

See CHANGELOG.md for full history.
```

- **Status — alternate shape:** No rolling date line; single pointer to CHANGELOG.md; no duplicate changelog sentences.

```markdown
## Status

No rolling "last updated" line here (manual upkeep only); chronological history: CHANGELOG.md.

What works now and what is in progress (two sentences max).
```

- **Date sourcing (default shape only):** Never guess **`YYYY-MM-DD`**. Prefer `date +%F` in the workspace; otherwise use a user-stated calendar date for the edit; if neither, ask once. Update the date when **Status** meaning changes; keep it for mechanical typo-only edits unless status text changes.
- **README ↔ MANUAL:** When **Automated setup** exists and the user names both README and **`MANUAL.md`**, finish README first if it gives context, then run **`/doc write manual`** separately for **`MANUAL.md`**.
- **Compliance:** No changelog edits out of scope; claims map to files read; TOC anchors match slugs per **`markdown-workflow.md`** when a TOC is used.
