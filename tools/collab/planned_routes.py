#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def die(message: str) -> None:
    raise SystemExit(message)


def source_text(path: Path) -> str:
    if not path.exists():
        return ''
    return path.read_text()


def issue_bridge_declared(config_root: Path) -> bool:
    if (config_root / '_functions/collab/export-issues.md').exists():
        return True
    command_text = '\n'.join([
        source_text(config_root / 'commands/collab.md'),
        source_text(config_root / 'commands/commands.md'),
    ])
    return '/collab export-issues' in command_text or 'export issues' in command_text


def issue_bridge_prerequisite_gaps(config_root: Path, include_issue_route: bool = False) -> list[str]:
    gaps: list[str] = []
    helper_output = source_text(config_root / '_functions/collab/_helper-output.md')
    helper_required = {
        'helper-output abort families': '## Abort families',
        'full-body envelope rejection': 'Full-body envelope rejection',
        'paired-execution-signature double-increment guard': 'Paired-execution-signature double-increment guard',
        'archive protocol violation': 'seal-verification-archive-protocol-violation',
        'logical module annotations': 'logical module',
    }
    helper_lower = helper_output.lower()
    for label, needle in helper_required.items():
        haystack = helper_lower if label == 'logical module annotations' else helper_output
        expected = needle.lower() if label == 'logical module annotations' else needle
        if expected not in haystack:
            gaps.append(label)

    rebinding_test = config_root / 'tests/tools/collab/registry.py/rebinding-invariants.test.sh'
    rebinding_text = source_text(rebinding_test)
    rebinding_required = {
        'rebinding invariant test file': '#!/usr/bin/env bash',
        'projectId rebinding coverage': 'projectId rebinding',
        'participant agentId rebinding coverage': 'agentId rebinding',
        'issue bridge gate coverage': 'issue bridge',
    }
    for label, needle in rebinding_required.items():
        if needle not in rebinding_text:
            gaps.append(label)

    if include_issue_route:
        issue_route = source_text(config_root / '_functions/git/issue.md')
        issue_route_required = {
            'issue output contract': 'Output contract',
            'issue caller-distinction': 'connector-backed',
            'issue owner metadata': 'Owner metadata',
            'issue requires preservation': '_requires:',
            'issue implement handoff shape': 'Implement handoff shape',
        }
        for label, needle in issue_route_required.items():
            if needle not in issue_route:
                gaps.append(label)
    return gaps


def workflow_model_selection_gaps(config_root: Path) -> list[str]:
    gaps: list[str] = []
    init_text = source_text(config_root / '_functions/collab/init.md')
    registry_text = source_text(config_root / '_functions/collab/_registry.md')
    helper_text = source_text(config_root / 'tools/collab/registry.py')

    init_required = {
        'init --terminal selector': '--terminal',
        'init route-arg --terminal': 'param: name=--terminal',
        'init terminal values': 'seal|issue',
    }
    for label, needle in init_required.items():
        if needle not in init_text:
            gaps.append(label)

    registry_required = {
        'registry terminal field': '`terminal`',
        'registry terminal enum': 'seal|issue',
    }
    for label, needle in registry_required.items():
        if needle not in registry_text:
            gaps.append(label)

    helper_required = {
        'helper --terminal parser': '--terminal',
        'helper terminal field persistence': "'terminal': terminal",
        'helper terminal validation': 'ALLOWED_TERMINALS',
    }
    for label, needle in helper_required.items():
        if needle not in helper_text:
            gaps.append(label)
    return gaps


def validate_issue_bridge_block(config_root: Path, include_issue_route: bool = False) -> None:
    if not issue_bridge_declared(config_root):
        return
    workflow_gaps = workflow_model_selection_gaps(config_root)
    if workflow_gaps:
        die(
            'workflow-model selection blocked: missing --terminal prerequisite(s): '
            f'{", ".join(workflow_gaps)}'
        )
    gaps = issue_bridge_prerequisite_gaps(config_root, include_issue_route)
    if gaps:
        issue_clause = (
            'third prerequisite: _functions/git/issue.md (output contract); '
            if include_issue_route else ''
        )
        die(
            'issue bridge blocked until prerequisite artifacts are present: '
            '_functions/collab/_helper-output.md and '
            'tests/tools/collab/registry.py/rebinding-invariants.test.sh; '
            f'{issue_clause}'
            f'missing {", ".join(gaps)}'
        )


def validate_planned_route_prerequisites(config_root: Path) -> None:
    validate_issue_bridge_block(config_root, include_issue_route=True)
