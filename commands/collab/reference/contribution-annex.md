# Contribution full body

Reference contract for storing an uncapped contribution body beside a capped human excerpt in a collab transcript.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** contribution full body, contribution annex, uncapped audit body, excerpt full body

## Steps

1. Read this document before changing contribution rendering, contribution word-count enforcement, contribution rewrite or retract behavior, transcript-read policy, or verification-seal binding.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The document is the tracked source record for the proposal formerly reviewed as "Contribution Annex for Uncapped Audit Bodies". The accepted design does not store prose in `registry.json` and does not create sibling annex files. The design keeps both contribution surfaces in the transcript:

- **Excerpt**: the visible contribution body. The excerpt is authored by the contributor and remains subject to the configured word limit.
- **Full body**: an optional uncapped body rendered by the helper as managed transcript structure immediately after the excerpt.

The helper-owned full-body block has exactly this envelope:

```html
<details>
<summary>Full contribution</summary>

[full body content]

</details>
```

Agents must not hand-author `<details>` blocks inside the excerpt surface. A contribution that needs uncapped body text passes it through the helper's full-body input, so the helper owns the envelope and can parse it deterministically.

## Parser contract

The canonical full-body block is recognized only when a `<details>` line is immediately followed by `<summary>Full contribution</summary>`. Any other `<details>` block in submitted excerpt text is rejected before mutation. The full-body content is byte-fenced; any `<details>` open or close tag inside the supplied full body is rejected before mutation.

Budgeting applies to the excerpt only. The canonical full-body block is excluded from the word count; non-canonical blocks are not exempt.

Rewrite replaces the active excerpt and active full body together. The prior active region, including any managed full body, is moved into revision history. Retract tombstones the active contribution and preserves the prior active region, including any managed full body, under retracted content.

## Read policy

Audit reads raw transcript content by default so the full body is available to the next contributor when the evidence load matters most. Later phases read rendered contribution content by default, which hides managed full-body blocks unless a route explicitly requests raw transcript content.

## Seal binding

Verification seals bind the exact managed full-body blocks in the transcript through a full-body signature. If those bytes change after sealing while the excerpt is unchanged, the existing seal becomes stale and must be reissued before a success verdict can close the record.
