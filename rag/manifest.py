"""Build a complete deterministic manifest for one source file."""

from __future__ import annotations

from pathlib import PurePosixPath

from rag.chunking import create_chunks
from rag.hierarchy import extract_hierarchy
from rag.records import FileManifest, FileRecord
from rag.source_config import (
    feature_for_path,
    language_for_path,
    source_kind_for_path,
)


def _line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def build_manifest(relative_path: PurePosixPath, text: str) -> FileManifest:
    """Build file metadata, hierarchy nodes, and linked chunks."""
    normalized_path = PurePosixPath(relative_path.as_posix())
    file_id = normalized_path.as_posix()
    language = language_for_path(normalized_path)
    nodes = extract_hierarchy(
        file_id=file_id,
        text=text,
        language=language,
    )
    chunks = create_chunks(
        file_id=file_id,
        text=text,
        language=language,
        nodes=nodes,
    )
    file_record = FileRecord(
        file_id=file_id,
        relative_path=normalized_path.as_posix(),
        filename=normalized_path.name,
        extension=normalized_path.suffix.lower(),
        language=language,
        source_kind=source_kind_for_path(normalized_path),
        feature=feature_for_path(normalized_path),
        size_bytes=len(text.encode("utf-8")),
        line_count=_line_count(text),
    )
    return FileManifest(file=file_record, nodes=nodes, chunks=chunks)
