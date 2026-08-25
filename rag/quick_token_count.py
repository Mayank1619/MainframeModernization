#!/usr/bin/env python3
"""Quick recursive token count across frontend and backend/api folders.

Usage:
  python rag/quick_token_count.py
    python rag/quick_token_count.py --root /path/to/MainframeModernization
  python rag/quick_token_count.py --use-tiktoken --encoding cl100k_base
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

WORD_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@dataclass
class FileStat:
    rel_path: str
    bytes_count: int
    line_count: int
    token_count: int


def iter_files(base_dirs: Iterable[Path], exclude_globs: list[str]) -> Iterable[Path]:
    for base in base_dirs:
        if not base.exists():
            continue
        for root, _, files in os.walk(base):
            root_path = Path(root)
            for name in files:
                file_path = root_path / name
                rel = str(file_path)
                if any(fnmatch.fnmatch(rel, pat) for pat in exclude_globs):
                    continue
                yield file_path


def approximate_token_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def build_token_counter(use_tiktoken: bool, encoding_name: str):
    if not use_tiktoken:
        return approximate_token_count, "regex-approx"

    try:
        import tiktoken  # type: ignore
    except Exception:
        return approximate_token_count, "regex-approx (tiktoken unavailable)"

    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except Exception:
        return approximate_token_count, f"regex-approx (unknown encoding: {encoding_name})"

    def tiktoken_count(text: str) -> int:
        return len(encoding.encode(text, disallowed_special=()))

    return tiktoken_count, f"tiktoken:{encoding_name}"


def count_file(file_path: Path, token_counter) -> FileStat | None:
    try:
        raw = file_path.read_bytes()
    except Exception:
        return None

    if b"\x00" in raw:
        return None

    text = raw.decode("utf-8", errors="ignore")
    rel_path = str(file_path)
    return FileStat(
        rel_path=rel_path,
        bytes_count=len(raw),
        line_count=text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        token_count=token_counter(text),
    )


def resolve_root(candidate_root: Path) -> tuple[Path, list[str]]:
    notes: list[str] = []

    if (candidate_root / "frontend").exists() and (candidate_root / "backend" / "api").exists():
        return candidate_root, notes

    children = [p for p in candidate_root.iterdir() if p.is_dir()]
    matches = [
        p
        for p in children
        if (p / "frontend").exists() and (p / "backend" / "api").exists()
    ]

    if len(matches) == 1:
        resolved = matches[0].resolve()
        notes.append(f"Auto-detected project root: {resolved}")
        return resolved, notes

    return candidate_root, notes


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick token count across frontend and backend/api folders")
    parser.add_argument(
        "--root",
        default=".",
        help="Project root that contains frontend/ and backend/api/ (default: current directory)",
    )
    parser.add_argument(
        "--use-tiktoken",
        action="store_true",
        help="Use tiktoken if installed for LLM-style token counting",
    )
    parser.add_argument(
        "--encoding",
        default="cl100k_base",
        help="tiktoken encoding name when --use-tiktoken is set (default: cl100k_base)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Show top N files by token count (default: 25)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob to exclude (repeatable), e.g. --exclude '*/node_modules/*'",
    )

    args = parser.parse_args()

    root_input = Path(args.root).resolve()
    root, notes = resolve_root(root_input)
    base_dirs = [root / "frontend", root / "backend" / "api"]
    token_counter, counter_name = build_token_counter(args.use_tiktoken, args.encoding)

    if not base_dirs[0].exists() or not base_dirs[1].exists():
        print(f"Root: {root}")
        print("Could not find both required folders: frontend/ and backend/api/")
        print("Fix: run from repo root, or pass --root /path/to/MainframeModernization")
        sys.exit(2)

    default_excludes = [
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
    exclude_globs = default_excludes + args.exclude

    stats: list[FileStat] = []
    for file_path in iter_files(base_dirs, exclude_globs):
        stat = count_file(file_path, token_counter)
        if stat is not None:
            stats.append(stat)

    stats.sort(key=lambda s: s.token_count, reverse=True)

    total_files = len(stats)
    total_bytes = sum(s.bytes_count for s in stats)
    total_lines = sum(s.line_count for s in stats)
    total_tokens = sum(s.token_count for s in stats)

    print(f"Root: {root}")
    for note in notes:
        print(note)
    print(f"Counted folders: {base_dirs[0]} and {base_dirs[1]}")
    print(f"Token counter: {counter_name}")
    print(f"Files counted: {total_files}")
    print(f"Total bytes: {total_bytes}")
    print(f"Total lines: {total_lines}")
    print(f"Total tokens: {total_tokens}")
    print()

    print(f"Top {min(args.top, total_files)} files by token count:")
    for s in stats[: args.top]:
        rel_display = Path(s.rel_path).resolve().relative_to(root)
        print(f"{s.token_count:>10} tokens  {s.line_count:>7} lines  {s.bytes_count:>10} bytes  {rel_display}")


if __name__ == "__main__":
    main()
