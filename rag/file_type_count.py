#!/usr/bin/env python3
"""Count distinct file types across frontend and backend/api.

Usage:
  python3 rag/file_type_count.py
  python3 rag/file_type_count.py --root /path/to/MainframeModernization
  python3 rag/file_type_count.py --exclude '*/target/*' --show-files
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDES = [
    "*/frontend/node_modules/*",
    "*/frontend/*/node_modules/*",
    "*/frontend/legacy-static/css/carbon-styles.min.css",
    "*/frontend/app/src/assets/*",
    '*/target/*' , '*/build/*' , '*/dist/*', '*/package-lock.json',
    '*/.DS_Store',
    '*/frontend/legacy-static/css/carbon-styles.min.css',
    '*/frontend/legacy-static/js/carbon-web-components.min.js',
    '*.class',
    '*.jar',
    '*.db',
    '*.svg',
     '*.png'
]


@dataclass
class FileTypeStat:
    count: int = 0
    total_bytes: int = 0


def resolve_root(candidate_root: Path) -> tuple[Path, list[str]]:
    notes: list[str] = []

    if (candidate_root / "frontend").exists() and (candidate_root / "backend" / "api").exists():
        return candidate_root, notes

    matches = [
        child
        for child in candidate_root.iterdir()
        if child.is_dir()
        and (child / "frontend").exists()
        and (child / "backend" / "api").exists()
    ]

    if len(matches) == 1:
        resolved = matches[0].resolve()
        notes.append(f"Auto-detected project root: {resolved}")
        return resolved, notes

    return candidate_root, notes


def is_excluded(file_path: Path, exclude_globs: list[str]) -> bool:
    absolute_path = str(file_path.resolve())
    return any(fnmatch.fnmatch(absolute_path, pattern) for pattern in exclude_globs)


def iter_files(base_dirs: Iterable[Path], exclude_globs: list[str]) -> Iterable[Path]:
    for base_dir in base_dirs:
        for root, _, filenames in os.walk(base_dir):
            root_path = Path(root)
            for filename in filenames:
                file_path = root_path / filename
                if not is_excluded(file_path, exclude_globs):
                    yield file_path


def file_type(file_path: Path) -> str:
    """Return a normalized extension while preserving extensionless dotfiles."""
    suffix = file_path.suffix.lower()
    if suffix:
        return suffix
    if file_path.name.startswith("."):
        return file_path.name.lower()
    return "[no extension]"


def format_bytes(byte_count: int) -> str:
    value = float(byte_count)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{byte_count} B"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count file types in frontend/ and backend/api/ with configurable exclusions"
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root containing frontend/ and backend/api/ (default: current directory)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional absolute-path glob to exclude; repeat for multiple rules",
    )
    parser.add_argument(
        "--show-files",
        action="store_true",
        help="List the files belonging to each file type after the summary",
    )
    args = parser.parse_args()

    root_input = Path(args.root).resolve()
    root, notes = resolve_root(root_input)
    base_dirs = [root / "frontend", root / "backend" / "api"]

    if not all(base_dir.exists() for base_dir in base_dirs):
        print(f"Root: {root}")
        print("Could not find both required folders: frontend/ and backend/api/")
        print("Run from the repository root or pass --root /path/to/MainframeModernization")
        sys.exit(2)

    exclude_globs = DEFAULT_EXCLUDES + args.exclude
    stats: dict[str, FileTypeStat] = defaultdict(FileTypeStat)
    files_by_type: dict[str, list[Path]] = defaultdict(list)

    for path in iter_files(base_dirs, exclude_globs):
        kind = file_type(path)
        try:
            byte_count = path.stat().st_size
        except OSError:
            byte_count = 0
        stats[kind].count += 1
        stats[kind].total_bytes += byte_count
        files_by_type[kind].append(path)

    ordered_types = sorted(stats, key=lambda kind: (-stats[kind].count, kind))
    total_files = sum(stat.count for stat in stats.values())
    total_bytes = sum(stat.total_bytes for stat in stats.values())

    print(f"Root: {root}")
    for note in notes:
        print(note)
    print(f"Counted folders: {base_dirs[0]} and {base_dirs[1]}")
    print(f"Files counted: {total_files}")
    print(f"Distinct file types: {len(stats)}")
    print(f"Total bytes: {total_bytes} ({format_bytes(total_bytes)})")
    print()
    print("File type counts:")
    for kind in ordered_types:
        stat = stats[kind]
        print(f"{kind:<28} -> {stat.count:>4} files  ({format_bytes(stat.total_bytes):>10})")

    if args.show_files:
        for kind in ordered_types:
            print()
            print(f"{kind}:")
            for path in sorted(files_by_type[kind]):
                print(f"  {path.resolve().relative_to(root)}")


if __name__ == "__main__":
    main()
