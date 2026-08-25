"""Incremental source-to-manifest ingestion application."""

from __future__ import annotations

from pathlib import PurePosixPath

import cocoindex as coco
from cocoindex.connectors import localfs
from cocoindex.resources.file import FileLike, PatternFilePathMatcher

from rag.manifest import build_manifest
from rag.source_config import (
    COCOINDEX_DB_PATH,
    EXCLUDED_PATTERNS,
    MANIFEST_ROOT,
    PROJECT_ROOT,
    SOURCE_ROOTS,
    SUPPORTED_FILENAMES,
    SUPPORTED_SUFFIXES,
    is_supported,
)


def _included_patterns() -> list[str]:
    extensions = ",".join(
        sorted(suffix.removeprefix(".") for suffix in SUPPORTED_SUFFIXES)
    )
    filenames = ",".join(sorted(SUPPORTED_FILENAMES))
    patterns: list[str] = []
    for root in SOURCE_ROOTS:
        patterns.append(f"{root.as_posix()}/**/*.{{{extensions}}}")
        patterns.append(f"{root.as_posix()}/**/{{{filenames}}}")
    return patterns


@coco.fn(memo=True)
async def process_file(file: FileLike, output_dir: coco.ContextKey) -> None:
    """Build and declare the manifest owned by one source file component."""
    resolved_path = file.file_path.resolve()
    relative_path = PurePosixPath(resolved_path.relative_to(PROJECT_ROOT).as_posix())
    if not is_supported(relative_path):
        return
    text = await file.read_text(errors="replace")
    manifest = build_manifest(relative_path, text)
    localfs.declare_file(
        output_dir / f"{relative_path.as_posix()}.json",
        manifest.to_json(),
        create_parent_dirs=True,
    )


@coco.fn
async def app_main(project_root: coco.ContextKey, output_dir: coco.ContextKey) -> None:
    matcher = PatternFilePathMatcher(
        included_patterns=_included_patterns(),
        excluded_patterns=EXCLUDED_PATTERNS,
    )
    files = localfs.walk_dir(
        project_root,
        live=True,
        recursive=True,
        path_matcher=matcher,
    )
    await coco.mount_each(process_file, files.items(), output_dir)


app = coco.App(
    coco.AppConfig(
        name="mainframe-modernization-rag-ingestion",
        environment=coco.Environment(coco.Settings(db_path=COCOINDEX_DB_PATH)),
    ),
    app_main,
    PROJECT_ROOT,
    MANIFEST_ROOT,
)
