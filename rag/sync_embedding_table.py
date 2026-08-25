"""Synchronize embedding-ready chunks into the local LanceDB table."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

try:
    from rag.source_config import RAG_ROOT
except ModuleNotFoundError:
    from source_config import RAG_ROOT


INPUT_ROOT = RAG_ROOT / "input_embeddings"
DATABASE_PATH = RAG_ROOT / "vector_store"
TABLE_NAME = "code_chunks"
EMBEDDING_DIMENSION = 768

OPERATIONAL_FIELDS = {
    "embedding",
    "embedding_status",
    "embedding_model",
    "embedding_model_revision",
    "embedding_dimension",
    "embedded_at",
    "embedding_error",
    "synced_at",
}


def chunk_schema(dimension: int = EMBEDDING_DIMENSION) -> pa.Schema:
    """Return the stable row schema used by synchronization and embedding."""
    return pa.schema(
        [
            pa.field("chunk_id", pa.string(), nullable=False),
            pa.field("file_id", pa.string(), nullable=False),
            pa.field("file_path", pa.string(), nullable=False),
            pa.field("filename", pa.string(), nullable=False),
            pa.field("extension", pa.string(), nullable=False),
            pa.field("language", pa.string()),
            pa.field("source_kind", pa.string(), nullable=False),
            pa.field("feature", pa.string()),
            pa.field("file_summary", pa.string(), nullable=False),
            pa.field("parent_node_id", pa.string()),
            pa.field("related_node_ids", pa.list_(pa.string()), nullable=False),
            pa.field("node_summary_texts", pa.list_(pa.string()), nullable=False),
            pa.field("chunk_index", pa.int32(), nullable=False),
            pa.field("start_line", pa.int32(), nullable=False),
            pa.field("end_line", pa.int32(), nullable=False),
            pa.field("token_count_approx", pa.int32(), nullable=False),
            pa.field("chunk_text", pa.string(), nullable=False),
            pa.field("embedding_text", pa.string(), nullable=False),
            pa.field("embedding_input_hash", pa.string(), nullable=False),
            pa.field("embedding_status", pa.string(), nullable=False),
            pa.field("embedding_model", pa.string()),
            pa.field("embedding_model_revision", pa.string()),
            pa.field("embedding_dimension", pa.int32()),
            pa.field("embedding", pa.list_(pa.float32(), dimension)),
            pa.field("embedded_at", pa.timestamp("us", tz="UTC")),
            pa.field("embedding_error", pa.string()),
            pa.field("synced_at", pa.timestamp("us", tz="UTC"), nullable=False),
        ]
    )


def _required_string(value: Any, label: str, source: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected non-empty {label} in {source}")
    return value


def _ordered_node_ids(chunk: dict[str, Any]) -> list[str]:
    node_ids: list[str] = []
    parent_id = chunk.get("parent_node_id")
    if parent_id:
        node_ids.append(parent_id)
    for node_id in chunk.get("related_node_ids", []):
        if node_id not in node_ids:
            node_ids.append(node_id)
    return node_ids


def _rows_from_manifest(path: Path, synced_at: datetime) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    file_record = payload.get("file")
    chunks = payload.get("chunks")
    nodes = payload.get("nodes", [])
    if not isinstance(file_record, dict) or not isinstance(chunks, list):
        raise ValueError(f"Invalid embedding manifest structure in {path}")
    if not isinstance(nodes, list):
        raise ValueError(f"Expected nodes to be a list in {path}")

    file_id = _required_string(file_record.get("file_id"), "file_id", path)
    file_summary = _required_string(file_record.get("summary"), "file summary", path)
    nodes_by_id = {
        node["node_id"]: node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("node_id"), str)
    }

    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise ValueError(f"Expected every chunk to be an object in {path}")
        chunk_id = _required_string(chunk.get("chunk_id"), "chunk_id", path)
        if chunk.get("file_id") != file_id:
            raise ValueError(f"Chunk {chunk_id} has the wrong file_id in {path}")
        embedding_text = _required_string(
            chunk.get("embedding_text"), "embedding_text", path
        )
        related_node_ids = _ordered_node_ids(chunk)
        node_summary_texts = []
        for node_id in related_node_ids:
            node = nodes_by_id.get(node_id)
            if node and node.get("summary"):
                name = node.get("qualified_name") or node.get("name") or node_id
                node_summary_texts.append(f"{name}: {node['summary']}")

        rows.append(
            {
                "chunk_id": chunk_id,
                "file_id": file_id,
                "file_path": file_record.get("relative_path") or file_id,
                "filename": _required_string(
                    file_record.get("filename"), "filename", path
                ),
                "extension": file_record.get("extension") or "",
                "language": file_record.get("language"),
                "source_kind": file_record.get("source_kind") or "production",
                "feature": file_record.get("feature"),
                "file_summary": file_summary,
                "parent_node_id": chunk.get("parent_node_id"),
                "related_node_ids": related_node_ids,
                "node_summary_texts": node_summary_texts,
                "chunk_index": int(chunk["chunk_index"]),
                "start_line": int(chunk["start_line"]),
                "end_line": int(chunk["end_line"]),
                "token_count_approx": int(chunk.get("token_count_approx", 0)),
                "chunk_text": _required_string(chunk.get("text"), "chunk text", path),
                "embedding_text": embedding_text,
                "embedding_input_hash": hashlib.sha256(
                    embedding_text.encode("utf-8")
                ).hexdigest(),
                "embedding_status": "pending",
                "embedding_model": None,
                "embedding_model_revision": None,
                "embedding_dimension": None,
                "embedding": None,
                "embedded_at": None,
                "embedding_error": None,
                "synced_at": synced_at,
            }
        )
    return rows


def load_embedding_rows(input_root: Path) -> list[dict[str, Any]]:
    """Load and validate every embedding-ready JSON file."""
    if not input_root.is_dir():
        raise FileNotFoundError(
            f"Embedding input folder does not exist: {input_root}. "
            "Run create_embedding_text.py first."
        )

    paths = sorted(input_root.glob("*.json"))
    if not paths:
        raise ValueError(f"Refusing to synchronize an empty input folder: {input_root}")

    synced_at = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    for path in paths:
        for row in _rows_from_manifest(path, synced_at):
            chunk_id = row["chunk_id"]
            if chunk_id in seen_chunk_ids:
                raise ValueError(f"Duplicate chunk_id: {chunk_id}")
            seen_chunk_ids.add(chunk_id)
            rows.append(row)
    if not rows:
        raise ValueError(f"No chunks were found in {input_root}")
    return rows


def _content_equal(existing: dict[str, Any], incoming: dict[str, Any]) -> bool:
    return all(
        existing.get(key) == value
        for key, value in incoming.items()
        if key not in OPERATIONAL_FIELDS
    )


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _delete_chunks(table: Any, chunk_ids: list[str], batch_size: int = 100) -> None:
    for start in range(0, len(chunk_ids), batch_size):
        batch = chunk_ids[start : start + batch_size]
        values = ", ".join(_sql_string(chunk_id) for chunk_id in batch)
        table.delete(f"chunk_id IN ({values})")


def synchronize(
    input_root: Path,
    database_path: Path,
    table_name: str,
    dimension: int,
    reset: bool = False,
) -> dict[str, int]:
    """Reconcile current chunks while preserving embeddings for unchanged text."""
    incoming_rows = load_embedding_rows(input_root)
    expected_schema = chunk_schema(dimension)
    database_path.mkdir(parents=True, exist_ok=True)
    database = lancedb.connect(database_path)

    table_names = set(database.list_tables().tables)
    if reset and table_name in table_names:
        database.drop_table(table_name)
        table_names.remove(table_name)

    if table_name not in table_names:
        table = database.create_table(table_name, schema=expected_schema)
        table.add(pa.Table.from_pylist(incoming_rows, schema=expected_schema))
        return {
            "total": len(incoming_rows),
            "inserted": len(incoming_rows),
            "changed": 0,
            "metadata_updated": 0,
            "unchanged": 0,
            "deleted": 0,
            "pending": len(incoming_rows),
            "ready": 0,
            "failed": 0,
        }

    table = database.open_table(table_name)
    if not table.schema.equals(expected_schema, check_metadata=False):
        raise ValueError(
            f"Table schema does not match the configured {dimension}-dimension schema. "
            "Run this script with --reset only if discarding existing vectors is intended."
        )

    existing_rows = {
        row["chunk_id"]: row for row in table.to_arrow().to_pylist()
    }
    incoming_ids = {row["chunk_id"] for row in incoming_rows}
    stale_ids = sorted(set(existing_rows) - incoming_ids)

    write_rows: list[dict[str, Any]] = []
    inserted = 0
    changed = 0
    metadata_updated = 0
    unchanged = 0
    for incoming in incoming_rows:
        existing = existing_rows.get(incoming["chunk_id"])
        if existing is None:
            inserted += 1
            write_rows.append(incoming)
            continue

        if existing["embedding_input_hash"] != incoming["embedding_input_hash"]:
            changed += 1
            write_rows.append(incoming)
            continue

        for field in OPERATIONAL_FIELDS:
            if field != "synced_at":
                incoming[field] = existing.get(field)
        if _content_equal(existing, incoming):
            unchanged += 1
            continue

        metadata_updated += 1
        write_rows.append(incoming)

    if write_rows:
        source = pa.Table.from_pylist(write_rows, schema=expected_schema)
        (
            table.merge_insert("chunk_id")
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute(source, on_bad_vectors="null")
        )
    if stale_ids:
        _delete_chunks(table, stale_ids)

    final_rows = table.to_arrow().to_pylist()
    statuses = [row["embedding_status"] for row in final_rows]
    return {
        "total": len(final_rows),
        "inserted": inserted,
        "changed": changed,
        "metadata_updated": metadata_updated,
        "unchanged": unchanged,
        "deleted": len(stale_ids),
        "pending": statuses.count("pending"),
        "ready": statuses.count("ready"),
        "failed": statuses.count("failed"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_ROOT)
    parser.add_argument("--database", type=Path, default=DATABASE_PATH)
    parser.add_argument("--table", default=TABLE_NAME)
    parser.add_argument("--dimension", type=int, default=EMBEDDING_DIMENSION)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the table, discarding existing embeddings.",
    )
    args = parser.parse_args()
    if args.dimension <= 0:
        parser.error("--dimension must be positive")

    stats = synchronize(
        input_root=args.input,
        database_path=args.database,
        table_name=args.table,
        dimension=args.dimension,
        reset=args.reset,
    )
    print(f"Synchronized LanceDB table '{args.table}' at {args.database}")
    print(
        "Chunks: {total} total | {inserted} new | {changed} text changed | "
        "{metadata_updated} metadata changed | {unchanged} unchanged | "
        "{deleted} deleted".format(**stats)
    )
    print(
        "Embedding state: {pending} pending | {ready} ready | {failed} failed".format(
            **stats
        )
    )


if __name__ == "__main__":
    main()
