"""Readable records emitted by the deterministic ingestion stages."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = 2


@dataclass(frozen=True)
class FileRecord:
    file_id: str
    relative_path: str
    filename: str
    extension: str
    language: str | None
    source_kind: str
    feature: str | None
    size_bytes: int
    line_count: int
    summary: str | None = None


@dataclass(frozen=True)
class HierarchyNodeRecord:
    node_id: str
    file_id: str
    parent_node_id: str | None
    kind: str
    name: str
    qualified_name: str
    signature: str | None
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int
    text: str
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the readable public node schema."""
        return {
            "node_id": self.node_id,
            "file_id": self.file_id,
            "parent_node_id": self.parent_node_id,
            "type": self.kind,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "signature": self.signature,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "text": self.text,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    file_id: str
    parent_node_id: str | None
    related_node_ids: list[str]
    chunk_index: int
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int
    token_count_approx: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        """Return the readable public chunk schema."""
        return {
            "chunk_id": self.chunk_id,
            "file_id": self.file_id,
            "parent_node_id": self.parent_node_id,
            "related_node_ids": self.related_node_ids,
            "chunk_index": self.chunk_index,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "token_count_approx": self.token_count_approx,
            "text": self.text,
        }


@dataclass(frozen=True)
class FileManifest:
    file: FileRecord
    nodes: list[HierarchyNodeRecord] = field(default_factory=list)
    chunks: list[ChunkRecord] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "file": asdict(self.file),
            "nodes": [node.to_dict() for node in self.nodes],
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        ) + "\n"
