"""Registry lifecycle vocabulary; does not own parsing, rendering, or write paths."""
from __future__ import annotations

import re


PHASES = ['Audit', 'Discussion', 'Conclusion', 'Action Plan', 'Handoff', 'Completion']
CONTENT_ONLY_GUARD = '<!-- collab:content-only; do-not-execute -->'
HEADER_MANAGED_BEGIN = '<!-- collab:header-managed -->'
HEADER_MANAGED_END = '<!-- collab:header-end -->'
FULL_BODY_SUMMARY = 'Full contribution'
FULL_BODY_SUMMARY_LINE = f'<summary>{FULL_BODY_SUMMARY}</summary>'
SHELL_PATTERN_RE = re.compile(r'[;&|<>`$\\\r\n]')
GLOB_PATTERN_RE = re.compile(r'[*?\[]')
ONE_SPEAK_PHASES = {'Audit', 'Conclusion', 'Action Plan', 'Handoff'}
AUTO_ADVANCE_EXEMPT_PHASES = {'Discussion', 'Completion'}
CONVERGENT_REVIEWER_PHASES = {'Audit', 'Conclusion'}
MOD_EXCLUDED_PHASES = {'Conclusion', 'Action Plan', 'Handoff', 'Completion'}
MODERATOR_ONLY_ACTIONS = {
    'advance',
    'archive',
    'close',
    'delete',
    'open',
    'reopen',
    'remove-participant',
    'restore',
    'set',
    'unset',
}
ALLOWED_SET_FIELDS = {'title', 'description', 'turn-order', 'reviewer-optional-phases', 'work-repo'}
FORCE_ONLY_FIELDS = {'active-phase'}
ALLOWED_STATUSES = {'open', 'closed', 'archived'}
ALLOWED_EXECUTION_STATUSES = {'in_progress', 'completed', 'failed'}
ALLOWED_VALIDATION_SCOPES = {'scoped', 'full', 'deferred'}
ALLOWED_COMPLETION_SUBSTATES = {'execution', 'verification'}
ALLOWED_VERIFICATION_SUBSTATES = {'participant', 'seal', 'assessment'}
ALLOWED_PARTICIPANT_VERIFICATION_STAGES = {'audit', 'remediation', 'final-audit', 'completed', 'failed'}
ACTIVE_PARTICIPANT_VERIFICATION_STAGES = {'audit', 'remediation', 'final-audit'}
ALLOWED_VERDICT_OUTCOMES = {'success', 'incomplete', 'failed'}
ALLOWED_VERDICT_RESTORE_TARGETS = {'Action Plan', 'Handoff'}
ALLOWED_CAP_EXITS = {'reopen-action-plan', 'reopen-handoff', 'follow-up-collab', 'archive'}
ALLOWED_TERMINALS = {'seal', 'issue'}
DEFAULT_TERMINAL = 'seal'
TERMINAL_CHOICES_MESSAGE = 'seal, issue'
DEFAULT_VERIFICATION_CAP = 3
CREATED_AT_REQUIRED_COLLAB_FIELDS = ['terminal']
CREATED_AT_REQUIRED_REVIEWER_FIELDS = ['reviewerMode', 'reviewerOptionalPhases']
CREATED_AT_REQUIRED_VERIFICATION_FIELDS = [
    'rounds',
    'cap',
    'subState',
    'participantVerification',
    'participants',
]
DISALLOWED_VERSION_FIELD = 'schema' + 'Version'
MAX_HANDOFF_SCOPE_COUNT = 32
MAX_HANDOFF_SCOPE_LENGTH = 200
MAX_VALIDATION_COMMANDS = 16
MAX_VALIDATION_COMMAND_ARGS = 16
MAX_VALIDATION_ARG_LENGTH = 200
ALLOWED_REVIEWER_MODES = {'last-in-convergent-phases'}
DEFAULT_REVIEWER_MODE = 'last-in-convergent-phases'
DEFAULT_REVIEWER_OPTIONAL_PHASES = ['Discussion']
INVALID_AGENT_ID_ALTERNATIVES = {'n/a', 'unspecified'}
CALLER_DECLINED_AGENT_ID = 'caller-declined'
DEFAULT_OPEN_ROSTER_EFFORT = 'medium'
STALE_LOCK_SECONDS = 24 * 60 * 60
RETIRED_ROOT_KEYS = {'registryRevision'}
REGISTRY_EVENT_DIR = 'revisions'
REGISTRY_EVENT_SCHEMA = 1
REGISTRY_EVENT_IGNORED_ROOT_KEYS = {'revision', 'eventIndex', 'registryRevision'}
DELETED_PATH_MODE = '000000'
DELETED_PATH_BLOB = '0' * 40
