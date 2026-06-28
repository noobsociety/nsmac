"""Read-only collab drift comparison helpers."""
from __future__ import annotations

import re
from pathlib import Path

from commands.collab.engine.contribution_store import (
    contribution_store_path_for_entry,
    mutable_contribution_store_for_entry,
)
from commands.collab.engine.digests import (
    content_digest_for_touched_paths,
    path_digest_at_ref,
    rendered_transcript_without_full_bodies,
)
from commands.collab.engine.git_repo import work_repo_root
from commands.collab.engine.registry_constants import (
    DELETED_PATH_BLOB,
    DELETED_PATH_MODE,
    HEADER_MANAGED_BEGIN,
    HEADER_MANAGED_END,
)
from commands.collab.engine.transcript_readers import (
    DETAILS_OPEN_RE,
    contribution_body_lines,
    contribution_is_retracted,
    summary_role,
)
from commands.collab.engine.transcript_render import (
    excerpt_source,
    is_scaffold_line,
    rendered_status_table,
)


SCAFFOLD_CATEGORY_SAMPLES = {
    'Contribution timestamp wrappers': '<p><em>2026-06-25 12:00 +00:00</em></p>',
    'Content-only guards': '<!-- collab:content-only; do-not-execute -->',
    'Effort-override banners': '<!-- collab:effort-override b64:RUZGT1JUIE9WRVJSSURFOiBsb3c= -->',
    'Full-contribution collapsible blocks': '\n'.join([
        'keep-before',
        '<details>',
        '<summary>Full contribution</summary>',
        '',
        'managed full body',
        '</details>',
        'keep-after',
    ]),
    'Managed header block': '\n'.join([
        'keep-before',
        HEADER_MANAGED_BEGIN,
        'managed header',
        HEADER_MANAGED_END,
        'keep-after',
    ]),
    'Revision-history collapsible blocks': '\n'.join([
        'keep-before',
        '<details><summary>Revision history</summary>',
        '',
        'Previous revision, 2026-06-25 12:00 +00:00:',
        '',
        'managed revision',
        '</details>',
        'keep-after',
    ]),
    'Action Plan checkbox state': '- [x] **pe:** [execute] Stable item text.',
}

SCAFFOLD_PREDICATE_CATEGORIES = {
    'transcript_render.is_scaffold_line': [
        'Contribution timestamp wrappers',
        'Content-only guards',
        'Effort-override banners',
    ],
    'digests.rendered_transcript_without_full_bodies': [
        'Full-contribution collapsible blocks',
    ],
    'diff.strip_managed_header_lines': [
        'Managed header block',
    ],
    'diff.strip_revision_history_lines': [
        'Revision-history collapsible blocks',
    ],
    'diff.normalize_action_plan_checkbox_marks': [
        'Action Plan checkbox state',
    ],
}


def ignored_scaffold_category_names() -> list[str]:
    return list(SCAFFOLD_CATEGORY_SAMPLES)


def scaffold_predicate_category_map() -> dict[str, list[str]]:
    return {key: list(value) for key, value in SCAFFOLD_PREDICATE_CATEGORIES.items()}


def strip_managed_header_lines(lines: list[str]) -> list[str]:
    stripped: list[str] = []
    in_header = False
    for line in lines:
        if line.strip() == HEADER_MANAGED_BEGIN:
            in_header = True
            continue
        if in_header:
            if line.strip() == HEADER_MANAGED_END:
                in_header = False
            continue
        stripped.append(line)
    return stripped


def strip_revision_history_lines(lines: list[str]) -> list[str]:
    stripped: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index].strip()
        inline = current == '<details><summary>Revision history</summary>'
        block = (
            DETAILS_OPEN_RE.match(current) is not None
            and index + 1 < len(lines)
            and lines[index + 1].strip() == '<summary>Revision history</summary>'
        )
        if inline or block:
            index = _details_block_end(lines, index)
            continue
        stripped.append(lines[index])
        index += 1
    return stripped


def normalize_action_plan_checkbox_marks(text: str) -> str:
    return re.sub(r'(^|\s)- \[[xX ]\] (\*\*[A-Za-z0-9_-]+:\*\*)', r'\1- [ ] \2', text)


def scaffold_stripped_text(text: str) -> str:
    without_full_bodies = rendered_transcript_without_full_bodies(text)
    lines = strip_managed_header_lines(without_full_bodies.splitlines())
    lines = strip_revision_history_lines(lines)
    lines = [line for line in lines if not is_scaffold_line(line)]
    rendered = '\n'.join(lines)
    if text.endswith('\n') and rendered:
        rendered += '\n'
    return rendered


def scaffold_category_results() -> dict[str, bool]:
    results: dict[str, bool] = {}
    for name, sample in SCAFFOLD_CATEGORY_SAMPLES.items():
        stripped = scaffold_stripped_text(sample)
        if name in {'Full-contribution collapsible blocks', 'Managed header block'}:
            results[name] = 'managed' not in stripped and 'keep-before' in stripped and 'keep-after' in stripped
        elif name == 'Revision-history collapsible blocks':
            results[name] = 'managed revision' not in stripped and 'keep-before' in stripped and 'keep-after' in stripped
        elif name == 'Action Plan checkbox state':
            results[name] = compact_excerpt(sample) == '- [ ] **pe:** [execute] Stable item text.'
        else:
            results[name] = stripped.strip() == ''
    return results


def compact_excerpt(text: str) -> str:
    stripped = scaffold_stripped_text(text)
    return normalize_action_plan_checkbox_marks(re.sub(r'\s+', ' ', excerpt_source(stripped)).strip())


def _details_block_end(lines: list[str], start: int) -> int:
    depth = 1
    index = start + 1
    while index < len(lines):
        stripped = lines[index].strip()
        if DETAILS_OPEN_RE.match(stripped):
            depth += 1
        elif stripped == '</details>':
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(lines)


def transcript_contribution_excerpts(transcript: str) -> dict[str, str]:
    lines = transcript.splitlines()
    excerpts: dict[str, str] = {}
    index = 0
    while index < len(lines):
        anchor = None
        anchor_match = re.match(r'^<a name="(?P<anchor>[A-Za-z0-9_-]+)"></a>$', lines[index].strip())
        if anchor_match:
            anchor = anchor_match.group('anchor')
            index += 1
        if index >= len(lines) or DETAILS_OPEN_RE.match(lines[index].strip()) is None:
            index += 1
            continue
        start = index
        end = _details_block_end(lines, start)
        block = lines[start:end]
        role = summary_role(block[1]) if len(block) > 1 else None
        if anchor and role and not contribution_is_retracted(block):
            excerpts[anchor] = compact_excerpt('\n'.join(contribution_body_lines(block)))
        index = end
    return excerpts


def stored_contribution_excerpts(registry_path: Path, entry: dict) -> dict[str, str]:
    path = contribution_store_path_for_entry(registry_path, entry)
    if not path.exists():
        return {}
    contributions = mutable_contribution_store_for_entry(registry_path, entry).get('contributions', [])
    excerpts: dict[str, str] = {}
    for item in contributions:
        if not isinstance(item, dict) or item.get('retracted') is True:
            continue
        anchor = item.get('anchor')
        if not isinstance(anchor, str) or not anchor:
            continue
        excerpt = item.get('excerpt')
        if not isinstance(excerpt, str):
            content = item.get('content')
            excerpt = compact_excerpt(content) if isinstance(content, str) else ''
        excerpts[anchor] = normalize_action_plan_checkbox_marks(re.sub(r'\s+', ' ', excerpt).strip())
    return excerpts


def content_mismatches(registry_path: Path, entry: dict, transcript: str) -> list[dict[str, str]]:
    stored = stored_contribution_excerpts(registry_path, entry)
    current = transcript_contribution_excerpts(transcript)
    rows: list[dict[str, str]] = []
    for anchor in sorted(set(stored) | set(current)):
        if anchor not in current:
            rows.append({'anchor': anchor, 'status': 'deleted', 'recorded': stored[anchor], 'current': ''})
        elif anchor not in stored:
            rows.append({'anchor': anchor, 'status': 'added', 'recorded': '', 'current': current[anchor]})
        elif stored[anchor] != current[anchor]:
            rows.append({'anchor': anchor, 'status': 'changed', 'recorded': stored[anchor], 'current': current[anchor]})
    return rows


def metadata_from_registry(entry: dict) -> dict[str, str]:
    return metadata_from_transcript(rendered_status_table(entry))


def metadata_from_transcript(transcript: str) -> dict[str, str]:
    lines = transcript.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == '| Status | Active phase | Turn order | Reviewer |':
            for candidate in lines[index + 2:]:
                stripped = candidate.strip()
                if not stripped.startswith('|'):
                    break
                cells = [cell.strip() for cell in stripped.strip('|').split('|')]
                if len(cells) >= 4:
                    return {
                        'Status': cells[0],
                        'Active phase': cells[1],
                        'Turn order': cells[2],
                        'Reviewer': cells[3],
                    }
    return {}


def metadata_mismatches(entry: dict, transcript: str) -> list[dict[str, str]]:
    registry = metadata_from_registry(entry)
    rendered = metadata_from_transcript(transcript)
    rows: list[dict[str, str]] = []
    for field, recorded in registry.items():
        current = rendered.get(field)
        if current != recorded:
            rows.append({'field': field, 'registry': recorded, 'transcript': current or '(missing)'})
    return rows


def seal_drift_rows(entry: dict) -> list[dict[str, str]]:
    seal = entry.get('verificationSeal')
    if not isinstance(seal, dict):
        return []
    recorded = seal.get('pathDigests')
    if not isinstance(recorded, dict):
        return []
    repo = work_repo_root(entry)
    rows: list[dict[str, str]] = []
    for path, digest in sorted(recorded.items()):
        if not isinstance(path, str) or not isinstance(digest, dict):
            continue
        recorded_mode = str(digest.get('mode', ''))
        recorded_blob = str(digest.get('blob', ''))
        current = path_digest_at_ref(repo, 'HEAD', path)
        if current is None:
            current_mode = DELETED_PATH_MODE
            current_blob = DELETED_PATH_BLOB
            status = 'deleted'
        else:
            current_mode = current.get('mode', '')
            current_blob = current.get('blob', '')
            status = 'changed'
        if recorded_mode != current_mode or recorded_blob != current_blob:
            rows.append({
                'path': path,
                'status': status,
                'recordedMode': recorded_mode,
                'recordedBlob': recorded_blob,
                'currentMode': current_mode,
                'currentBlob': current_blob,
            })
    return rows


def diff_result(registry_path: Path, entry: dict, transcript: str) -> dict:
    # Recompute through the digest owner as a reuse guard; seal_drift_rows reports path rows.
    touched = list((entry.get('verificationSeal') or {}).get('pathDigests', {}).keys()) if isinstance(entry.get('verificationSeal'), dict) else []
    if touched:
        repo = work_repo_root(entry)
        present_touched = [path for path in touched if path_digest_at_ref(repo, 'HEAD', path) is not None]
        if present_touched:
            content_digest_for_touched_paths(repo, 'HEAD', present_touched)
    return {
        'target': entry.get('id'),
        'sealDrift': seal_drift_rows(entry),
        'contentMismatch': content_mismatches(registry_path, entry, transcript),
        'metadataMismatch': metadata_mismatches(entry, transcript),
    }


def _short_blob(blob: str) -> str:
    if blob == DELETED_PATH_BLOB:
        return '(deleted)'
    return blob


def render_diff(result: dict) -> str:
    lines = [f"collab diff: {result.get('target', '(unknown)')}"]
    seal_rows = result.get('sealDrift', [])
    lines.append(f"seal drift ({len(seal_rows)} paths):")
    if seal_rows:
        for row in seal_rows:
            lines.extend([
                f"  {row['path']}",
                f"    recorded blob: {_short_blob(row['recordedBlob'])}  mode: {row['recordedMode']}",
                f"    current  blob: {_short_blob(row['currentBlob'])}  mode: {row['currentMode']}",
                f"    status: {row['status']}",
            ])
    else:
        lines.append('  (none)')

    content_rows = result.get('contentMismatch', [])
    lines.append(f"content mismatch ({len(content_rows)} contributions):")
    if content_rows:
        for row in content_rows:
            lines.extend([
                f"  {row['anchor']}: {row['status']}",
                f"    recorded: {row['recorded'] or '(none)'}",
                f"    current: {row['current'] or '(none)'}",
            ])
    else:
        lines.append('  (none)')

    metadata_rows = result.get('metadataMismatch', [])
    lines.append(f"metadata mismatch ({len(metadata_rows)} fields):")
    if metadata_rows:
        for row in metadata_rows:
            lines.append(f"  {row['field']}: registry={row['registry']} transcript={row['transcript']}")
    else:
        lines.append('  (none)')
    return '\n'.join(lines) + '\n'
