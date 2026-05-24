#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


LEDGER_PATH = Path("data/source-ledger.md")
REQUIRED_COLUMNS = [
    "source path",
    "normative essence",
    "destination owner",
    "load contract",
    "validation check",
    "delete condition",
]
SCAN_DIRS = [
    "templates",
    "tests/specs",
    "generated",
    "settings",
    "core/framework",
    "commands",
    "core",
    "tests",
    "tools",
]
RETIRED_ROOT_ADAPTER = "_" + "CUR" + "SOR.md"
RETIRED_PREFIX = "cur" + "sor"
LEGACY_TRACE_RE = re.compile(
    r"(?P<trace>"
    + re.escape(RETIRED_ROOT_ADAPTER)
    + r"|(?<![A-Za-z0-9_-])"
    + RETIRED_PREFIX
    + r"-(?:arg|flag|gate)(?![A-Za-z0-9_-])"
    + r"|alwaysApply|globs:|(?:^|[`\s\"'(/])(?:rules|_mdc)/[^`\s\"')]+|[A-Za-z0-9_-]+\.mdc)"
)
ALLOWLISTED_TRACE_PATHS = {
    "tools/command-system/check-source-ledger.py",
    "tools/command-system/sync-context-gate.sh",
    "data/source-ledger.md",
    "tests/tools/command-system/check-source-ledger.test.sh",
    "tests/tools/command-system/sync-context-gate.test.sh",
    "tests/tools/narrative/state.py/gate-enforcement.test.sh",
}


@dataclass(frozen=True)
class LedgerRow:
    source: str
    cells: list[str]
    line: int


@dataclass(frozen=True)
class Failure:
    path: Path
    line: int
    message: str

    def render(self) -> str:
        return f"FAIL: {self.path}:{self.line}: {self.message}"


def run_git_ls_files(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def normalize_source_cell(cell: str) -> str:
    value = cell.strip().replace("`", "")
    return re.sub(r"\s+", " ", value).strip()


def parse_ledger(root: Path, ledger: Path) -> tuple[list[LedgerRow], list[Failure]]:
    failures: list[Failure] = []
    path = root / ledger
    if not path.exists():
        return [], [Failure(ledger, 1, "missing source ledger")]

    rows: list[LedgerRow] = []
    expected_header = REQUIRED_COLUMNS
    in_migration_table = False
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        cells = split_markdown_row(line)
        if not cells:
            in_migration_table = False
            continue
        lowered = [cell.lower() for cell in cells]
        if lowered == expected_header:
            in_migration_table = True
            continue
        if is_separator_row(cells):
            continue
        if not in_migration_table:
            continue
        if len(cells) != len(REQUIRED_COLUMNS):
            failures.append(
                Failure(
                    ledger,
                    number,
                    f"ledger row must have {len(REQUIRED_COLUMNS)} columns",
                )
            )
            continue
        missing = [
            REQUIRED_COLUMNS[index]
            for index, cell in enumerate(cells)
            if not cell.strip()
        ]
        if missing:
            failures.append(
                Failure(ledger, number, f"ledger row missing fields: {', '.join(missing)}")
            )
            continue
        source = normalize_source_cell(cells[0])
        rows.append(LedgerRow(source=source, cells=cells, line=number))

    seen: dict[str, int] = {}
    for row in rows:
        previous = seen.get(row.source)
        if previous is not None:
            failures.append(Failure(ledger, row.line, f"duplicate source path: {row.source}"))
        seen[row.source] = row.line

    return rows, failures


def discover_carriers(root: Path) -> set[str]:
    carriers: set[str] = set()
    for path in sorted((root / "rules").glob("*.mdc")):
        carriers.add(path.relative_to(root).as_posix())
    for path in sorted((root / "_mdc").rglob("*.mdc")):
        carriers.add(path.relative_to(root).as_posix())
    if (root / RETIRED_ROOT_ADAPTER).exists():
        carriers.add(RETIRED_ROOT_ADAPTER)
    return carriers


def check_inventory(root: Path, rows: list[LedgerRow]) -> list[Failure]:
    declared = {row.source for row in rows}
    failures: list[Failure] = []
    for source in sorted(discover_carriers(root) - declared):
        failures.append(Failure(LEDGER_PATH, 1, f"discovered carrier lacks ledger row: {source}"))
    return failures


def normalize_reference(raw: str) -> str:
    value = raw.strip("`'\"([]),.;:]}")
    value = value.removeprefix("~/.cursor/")
    while value.startswith(("../", "./", "/")):
        if value.startswith("/"):
            value = value[1:]
            continue
        value = value[3:]
    return value


def iter_scan_files(root: Path) -> list[Path]:
    tracked = run_git_ls_files(root)
    files: list[Path] = []
    for dirname in SCAN_DIRS:
        base = root / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(root).as_posix()
            if tracked and rel not in tracked and not rel.startswith("tests/fixtures/"):
                continue
            files.append(path)
    return sorted(files)


def check_dependency_scan(root: Path) -> list[Failure]:
    failures: list[Failure] = []
    for path in iter_scan_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in ALLOWLISTED_TRACE_PATHS:
            continue
        try:
            lines = path.read_text(errors="strict").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            match = LEGACY_TRACE_RE.search(line)
            if match:
                failures.append(
                    Failure(
                        Path(rel),
                        number,
                        f"retired substrate trace: {match.group('trace').strip()}",
                    )
                )
    return failures


def check(root: Path, ledger: Path) -> int:
    rows, failures = parse_ledger(root, ledger)
    if rows:
        failures.extend(check_inventory(root, rows))
        failures.extend(check_dependency_scan(root))

    if failures:
        for failure in failures:
            print(failure.render(), file=sys.stderr)
        return 1
    print("OK: source ledger, carrier inventory, and dependency scan pass")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="run the migration checks")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--ledger", default=str(LEDGER_PATH), help="ledger path relative to root")
    args = parser.parse_args(argv)

    if not args.check:
        parser.error("only --check is supported")

    root = Path(args.root).resolve()
    return check(root, Path(args.ledger))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
