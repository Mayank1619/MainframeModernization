"""Syntax-aware chunk creation and hierarchy linking."""

from __future__ import annotations

import re

from cocoindex.ops.text import RecursiveSplitter

from rag.records import ChunkRecord, HierarchyNodeRecord


CHUNK_SIZE_BYTES = 2400
MIN_CHUNK_SIZE_BYTES = 500
CHUNK_OVERLAP_BYTES = 0

_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_SPLITTER = RecursiveSplitter()


def approximate_token_count(text: str) -> int:
    return len(_TOKEN_RE.findall(text))


def _containing_node(
    nodes: list[HierarchyNodeRecord], start_byte: int, end_byte: int
) -> HierarchyNodeRecord | None:
    containing = [
        node
        for node in nodes
        if node.start_byte <= start_byte and end_byte <= node.end_byte
    ]
    if not containing:
        return None
    return min(containing, key=lambda node: node.end_byte - node.start_byte)


def _related_node_ids(
    nodes: list[HierarchyNodeRecord], start_byte: int, end_byte: int
) -> list[str]:
    related = [
        node
        for node in nodes
        if node.start_byte < end_byte and start_byte < node.end_byte
    ]
    related.sort(key=lambda node: (node.start_byte, node.end_byte, node.node_id))
    return [node.node_id for node in related]


def create_chunks(
    *,
    file_id: str,
    text: str,
    language: str | None,
    nodes: list[HierarchyNodeRecord],
) -> list[ChunkRecord]:
    """Split one file and link each chunk to extracted hierarchy nodes."""
    if not text:
        return []

    try:
        chunks = _SPLITTER.split(
            text,
            CHUNK_SIZE_BYTES,
            min_chunk_size=MIN_CHUNK_SIZE_BYTES,
            chunk_overlap=CHUNK_OVERLAP_BYTES,
            language=language,
        )
    except Exception:
        chunks = _SPLITTER.split(
            text,
            CHUNK_SIZE_BYTES,
            min_chunk_size=MIN_CHUNK_SIZE_BYTES,
            chunk_overlap=CHUNK_OVERLAP_BYTES,
        )

    records: list[ChunkRecord] = []
    for zero_based_index, chunk in enumerate(chunks):
        chunk_index = zero_based_index + 1
        parent = _containing_node(
            nodes,
            chunk.start.byte_offset,
            chunk.end.byte_offset,
        )
        chunk_id = f"{file_id}::chunk-{chunk_index:04d}"
        records.append(
            ChunkRecord(
                chunk_id=chunk_id,
                file_id=file_id,
                parent_node_id=parent.node_id if parent else None,
                related_node_ids=_related_node_ids(
                    nodes,
                    chunk.start.byte_offset,
                    chunk.end.byte_offset,
                ),
                chunk_index=chunk_index,
                start_byte=chunk.start.byte_offset,
                end_byte=chunk.end.byte_offset,
                start_line=chunk.start.line,
                end_line=chunk.end.line,
                token_count_approx=approximate_token_count(chunk.text),
                text=chunk.text,
            )
        )

    return records
