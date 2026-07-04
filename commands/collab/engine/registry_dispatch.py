#!/usr/bin/env python3
"""Table-driven CLI dispatch for commands/collab/engine/registry.py."""
from __future__ import annotations

import os
from pathlib import Path
from types import ModuleType
from typing import Callable

from commands.collab.engine.errors import die
from commands.collab.engine.release import release_collab, tag_collab
from commands.collab.engine.registry_parser import build_parser, render_registry_cli_doc

ROOT = Path(__file__).resolve().parents[3]
Handler = Callable[[ModuleType, object, Path], int]


def _normalize_file_args(args: object) -> None:
    for path_arg in ('content_file', 'full_body_file', 'summary_file', 'evidence_file'):
        if hasattr(args, path_arg) and getattr(args, path_arg):
            setattr(args, path_arg, str(Path(getattr(args, path_arg)).resolve()))


def _registry_path_for_args(ctx: ModuleType, args: object) -> Path:
    registry = getattr(args, 'registry')
    if registry is not None:
        return Path(registry)
    path, use_state_root = ctx.resolve_default_registry_path(args.command)
    if use_state_root:
        identity_path = ctx.find_project_identity_path(Path.cwd())
        if identity_path is not None:
            ctx.set_resolved_work_repo_root(identity_path.parent)
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chdir(path.parent)
    return path


def _validate(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.validate_command(path)


def _registry_path(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.registry_path_command(path)


def _registry_cli_doc(ctx: ModuleType, args: object, path: Path) -> int:
    rendered = render_registry_cli_doc()
    generated_path = ROOT / 'generated/registry-cli.md'
    if args.check:
        if not generated_path.exists() or generated_path.read_text() != rendered:
            die('generated/registry-cli.md is stale; run commands/collab/engine/registry.py registry-cli-doc > generated/registry-cli.md')
        return 0
    print(rendered, end='')
    return 0


def _list(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.list_collabs(ctx.load_registry(path), args.status)


def _log(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.log_command(path, args.target)


def _flag_inventory(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.flag_inventory(Path(args.spec))


def _help(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.route_help_command(args.route)


def _timestamp(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.timestamp_command()


def _banner_timestamp(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.banner_timestamp_command()


def _role_row(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.role_row_command(Path(args.roles_dir), args.role, args.index)


def _roles(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.roles_command(Path(args.roles_dir))


def _summary_role(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.summary_role_command(args.line)


def _reviewer_state(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.reviewer_state_command(path, args.target)


def _handoff_state(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.handoff_state_command(path, args.target, args.role)


def _activate(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.activate_collab(path, args.target)


def _open(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.open_collab(path, args.target, args.caller_role)


def _init(ctx: ModuleType, args: object, path: Path) -> int:
    tokens: list[str] = []
    for agent_id in args.agent_id or []:
        tokens.extend(['--agent-id', agent_id])
    for reviewer in args.reviewer or []:
        tokens.extend(['--reviewer', reviewer])
    for terminal in args.terminal or []:
        tokens.extend(['--terminal', terminal])
    for work_repo in args.work_repo or []:
        tokens.extend(['--work-repo', work_repo])
    if not args.participant_verification:
        tokens.append('--no-participant-verification')
    if args.open:
        tokens.append('--open')
    tokens.extend(args.name)
    return ctx.init_collab(path, tokens, ctx.DEFAULT_ROLES_DIR)


def _join_participants(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.join_participants(path, args.target, args.role, args.agent_id, Path(args.roles_dir), args.json)


def _remove_participant(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.remove_participant(path, args.target, args.role, Path(args.roles_dir), args.caller_role)


def _set(ctx: ModuleType, args: object, path: Path) -> int:
    value = '--clear' if args.clear else args.value
    return ctx.set_field(path, args.target, args.field, value, args.force, Path(args.roles_dir), args.caller_role)


def _unset(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.unset_field(path, args.target, args.field, Path(args.roles_dir), args.caller_role)


def _effort_state(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.effort_state(path, args.target, args.role, Path(args.effort_defaults))


def _audit_effort_matrix(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.audit_effort_matrix(Path(args.effort_defaults), Path(args.agent_model))


def _speak_lifecycle(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.speak_lifecycle(path, args.target, args.contributors)


def _speak_state(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.speak_state(path, args.target, args.role, args.resume)


def _speak_lifecycle_live(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.speak_lifecycle_live(path, args.target)


def _speak_render(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.render_speak(
        path,
        args.target,
        args.role,
        Path(args.content_file),
        Path(args.full_body_file) if args.full_body_file else None,
        args.observed_revision,
        args.timestamp,
        args.json,
        args.caller_role,
        args.verbatim,
    )


def _rewrite_speak_render(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.render_re_speak(
        path,
        args.target,
        args.role,
        Path(args.content_file),
        Path(args.full_body_file) if args.full_body_file else None,
        args.timestamp,
        args.caller_role,
        args.verbatim,
    )


def _retract_speak(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.retract_latest_contribution(path, args.target, args.role, args.reason, args.timestamp, args.caller_role)


def _advance(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.advance_phase(path, args.target, args.direction, args.json, args.caller_role)


def _restore(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.restore_collab_content(path, args.target, args.to, args.caller_role)


def _execution(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.record_execution(
        path,
        args.target,
        args.role,
        args.status,
        args.date,
        args.assigned_role,
        args.auto_close,
        args.validation_result,
        args.validation_scope,
        args.touched_path,
        args.agent_id,
        args.json,
        args.caller_role,
    )


def _export_issues(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.export_issues(
        path,
        args.target,
        args.role,
        Path(args.evidence_file),
        args.timestamp,
        args.json,
        args.caller_role,
    )


def _repair_execution_provenance(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.repair_execution_provenance(
        path,
        args.target,
        args.role,
        args.work_repo,
        args.commit,
        args.caller_role,
    )


def _tag(ctx: ModuleType, args: object, path: Path) -> int:
    return tag_collab(
        path,
        args.target,
        args.tag_name,
        args.confirm,
        args.push,
        args.caller_role,
    )


def _release(ctx: ModuleType, args: object, path: Path) -> int:
    return release_collab(
        path,
        args.target,
        args.tag_name,
        args.confirm,
        args.push,
        args.direct_merge,
        args.github_release,
        args.auto_fire,
        args.caller_role,
    )


def _execute_spawn(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.execute_spawn(path, args.target, args.role, args.scope, args.sibling_scope, args.returned_path)


def _transcript_repair(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.transcript_repair(path, args.target, args.touch_execution_evidence, args.caller_role)


def _out_of_scope_patch(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.out_of_scope_patch(path, args.target, args.role, args.path, args.caller_role)


def _transcript_view(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.transcript_view(path, args.target, args.phase, args.raw)


def _summarize(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.summarize_collab(path, args.target, args.date)


def _participant_verify_state(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.participant_verify_state(path, args.target, args.role, args.resume)


def _participant_verify_render(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.participant_verify_render(
        path,
        args.target,
        args.role,
        args.observed_revision,
        args.audit_file,
        args.remediation_file,
        args.final_audit_file,
        args.status,
        args.touched_path,
        args.execution_agent_id,
        args.audit_agent_id,
        args.remediation_agent_id,
        args.timestamp,
        args.caller_role,
    )


def _seal_state(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.seal_state(path, args.target, args.role, args.resume)


def _seal_render(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.render_seal(
        path,
        args.target,
        args.role,
        args.observed_revision,
        args.cap_exit,
        args.outcome,
        args.restore_target,
        args.restore_reason,
        args.evidence,
        args.failure_category,
        args.null_result,
        args.json,
        args.caller_role,
    )


def _seal_write(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx._seal_verification_render.seal_write(
        path,
        args.target,
        args.role,
        args.observed_revision,
        args.cap_exit,
        args.restore_reason,
        args.evidence,
        args.failure_category,
        args.json,
        args.caller_role,
    )


def _record_verdict(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx._seal_verification_render.record_verdict(
        path,
        args.target,
        args.role,
        args.observed_revision,
        args.outcome,
        args.restore_target,
        args.restore_reason,
        args.evidence,
        args.failure_category,
        args.null_result,
        args.json,
        args.caller_role,
    )


def _restart_verification(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.restart_verification(path, args.target, args.caller_role)


def _reopen(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.reopen_collab(path, args.target, args.phase, args.caller_role)


def _show_verdict(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.show_verdict(path, args.target)


def _rewrite_summary(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.re_summarize_collab(path, args.target, Path(args.summary_file), args.date)


def _close(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.close_collab(path, args.target, args.json, args.caller_role)


def _audit_closed(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.audit_closed(path)


def _archive(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.archive_collab(path, args.target, args.json, args.caller_role)


def _delete(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.delete_collab(path, args.target, args.yes, args.caller_role)


def _diff(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.diff_command(path, args.target)


def _render_status(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.render_status(path, args.target)


def _status_view(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.status_view(path, args.target)


def _render_participants(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.render_participants(path, args.target, Path(args.roles_dir))


def _write_guard(ctx: ModuleType, args: object, path: Path) -> int:
    return ctx.write_guard(args.route, args.paths)


DISPATCH: dict[str, Handler] = {
    'activate': _activate,
    'advance': _advance,
    'archive': _archive,
    'audit-closed': _audit_closed,
    'audit-effort-matrix': _audit_effort_matrix,
    'banner-timestamp': _banner_timestamp,
    'close': _close,
    'delete': _delete,
    'diff': _diff,
    'effort-state': _effort_state,
    'execute-spawn': _execute_spawn,
    'execution': _execution,
    'export-issues': _export_issues,
    'flag-inventory': _flag_inventory,
    'handoff-state': _handoff_state,
    'help': _help,
    'init': _init,
    'join-participants': _join_participants,
    'list': _list,
    'log': _log,
    'open': _open,
    'out-of-scope-patch': _out_of_scope_patch,
    'participant-verify-render': _participant_verify_render,
    'participant-verify-state': _participant_verify_state,
    'record-verdict': _record_verdict,
    'release': _release,
    'registry-cli-doc': _registry_cli_doc,
    'registry-path': _registry_path,
    'remove-participant': _remove_participant,
    'render-participants': _render_participants,
    'render-status': _render_status,
    'reopen': _reopen,
    'repair-execution-provenance': _repair_execution_provenance,
    'restart-verification': _restart_verification,
    'restore': _restore,
    'retract-speak': _retract_speak,
    'reviewer-state': _reviewer_state,
    'rewrite-speak-render': _rewrite_speak_render,
    'rewrite-summary': _rewrite_summary,
    'role-row': _role_row,
    'roles': _roles,
    'seal-render': _seal_render,
    'seal-state': _seal_state,
    'seal-write': _seal_write,
    'set': _set,
    'show-verdict': _show_verdict,
    'speak-lifecycle': _speak_lifecycle,
    'speak-lifecycle-live': _speak_lifecycle_live,
    'speak-render': _speak_render,
    'speak-state': _speak_state,
    'status-view': _status_view,
    'summarize': _summarize,
    'summary-role': _summary_role,
    'tag': _tag,
    'timestamp': _timestamp,
    'transcript-repair': _transcript_repair,
    'transcript-view': _transcript_view,
    'unset': _unset,
    'validate': _validate,
    'write-guard': _write_guard,
}


def main(argv: list[str], ctx: ModuleType | None = None) -> int:
    if ctx is None:
        from commands.collab.engine import registry_core as ctx

    parser = build_parser()
    args, unknown_args = parser.parse_known_args(argv)
    if unknown_args:
        if args.command == 'init':
            for item in unknown_args:
                if item.startswith('--'):
                    die(f'unknown flag: {item}')
        parser.error(f'unrecognized arguments: {" ".join(unknown_args)}')
    _normalize_file_args(args)
    path = _registry_path_for_args(ctx, args)
    try:
        handler = DISPATCH[args.command]
    except KeyError:
        parser.error(f'unknown command: {args.command}')
        return 2
    return handler(ctx, args, path)
