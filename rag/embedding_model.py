"""Embed pending LanceDB chunk rows with the local CodeRankEmbed model."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

try:
    from rag.sync_embedding_table import (
        DATABASE_PATH,
        EMBEDDING_DIMENSION,
        TABLE_NAME,
        chunk_schema,
    )
except ModuleNotFoundError:
    from sync_embedding_table import (
        DATABASE_PATH,
        EMBEDDING_DIMENSION,
        TABLE_NAME,
        chunk_schema,
    )


MODEL_NAME = "nomic-ai/CodeRankEmbed"
MODEL_REVISION = "3c4b60807d71f79b43f3c4363786d9493691f8b1"


def _needs_embedding(
    row: dict[str, Any],
    model_name: str,
    model_revision: str,
    dimension: int,
    force: bool,
) -> bool:
    embedding = row.get("embedding")
    return (
        force
        or row.get("embedding_status") != "ready"
        or embedding is None
        or len(embedding) != dimension
        or row.get("embedding_model") != model_name
        or row.get("embedding_model_revision") != model_revision
        or row.get("embedding_dimension") != dimension
    )


def _write_rows(table: Any, rows: list[dict[str, Any]], dimension: int) -> None:
    source = pa.Table.from_pylist(rows, schema=chunk_schema(dimension))
    (
        table.merge_insert("chunk_id")
        .when_matched_update_all()
        .execute(source, on_bad_vectors="null")
    )


def embed_pending_rows(
    database_path: Path,
    table_name: str,
    model_name: str,
    model_revision: str,
    batch_size: int,
    device: str | None,
    limit: int | None,
    force: bool,
) -> dict[str, int]:
    """Generate vectors only for rows that are absent, stale, or failed."""
    database = lancedb.connect(database_path)
    if table_name not in set(database.list_tables().tables):
        raise FileNotFoundError(
            f"LanceDB table '{table_name}' does not exist at {database_path}. "
            "Run sync_embedding_table.py first."
        )
    table = database.open_table(table_name)

    model_kwargs: dict[str, Any] = {
        "revision": model_revision,
        "trust_remote_code": True,
    }
    if device:
        model_kwargs["device"] = device
    print(f"Loading {model_name} at revision {model_revision}...")
    model = SentenceTransformer(model_name, **model_kwargs)
    dimension = model.get_sentence_embedding_dimension()
    if not dimension:
        raise ValueError(f"Could not determine the output dimension for {model_name}")
    if dimension != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Model outputs {dimension} dimensions, but the table expects "
            f"{EMBEDDING_DIMENSION}. Recreate the table with the matching dimension."
        )

    expected_schema = chunk_schema(dimension)
    if not table.schema.equals(expected_schema, check_metadata=False):
        raise ValueError(
            f"Table schema is incompatible with {dimension}-dimension embeddings."
        )

    all_rows = table.to_arrow().to_pylist()
    pending_rows = [
        row
        for row in all_rows
        if _needs_embedding(
            row,
            model_name=model_name,
            model_revision=model_revision,
            dimension=dimension,
            force=force,
        )
    ]
    if limit is not None:
        pending_rows = pending_rows[:limit]
    if not pending_rows:
        return {"total": len(all_rows), "selected": 0, "embedded": 0, "failed": 0}

    embedded = 0
    failed = 0
    for start in range(0, len(pending_rows), batch_size):
        batch = pending_rows[start : start + batch_size]
        try:
            vectors = model.encode(
                [row["embedding_text"] for row in batch],
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            embedded_at = datetime.now(timezone.utc)
            for row, vector in zip(batch, vectors, strict=True):
                if vector.shape != (dimension,):
                    raise ValueError(
                        f"Unexpected vector shape {vector.shape} for {row['chunk_id']}"
                    )
                row["embedding"] = vector.astype("float32", copy=False).tolist()
                row["embedding_status"] = "ready"
                row["embedding_model"] = model_name
                row["embedding_model_revision"] = model_revision
                row["embedding_dimension"] = dimension
                row["embedded_at"] = embedded_at
                row["embedding_error"] = None
            _write_rows(table, batch, dimension)
            embedded += len(batch)
            print(f"Embedded {embedded}/{len(pending_rows)} selected chunks")
        except Exception as error:
            failed_at = datetime.now(timezone.utc)
            message = f"{type(error).__name__}: {error}"[:2000]
            for row in batch:
                row["embedding"] = None
                row["embedding_status"] = "failed"
                row["embedding_model"] = model_name
                row["embedding_model_revision"] = model_revision
                row["embedding_dimension"] = dimension
                row["embedded_at"] = failed_at
                row["embedding_error"] = message
            _write_rows(table, batch, dimension)
            failed += len(batch)
            print(f"Failed batch starting at row {start + 1}: {message}")

    return {
        "total": len(all_rows),
        "selected": len(pending_rows),
        "embedded": embedded,
        "failed": failed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DATABASE_PATH)
    parser.add_argument("--table", default=TABLE_NAME)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument(
        "--device",
        help="Optional SentenceTransformer device, such as mps or cpu.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Embed only the first N pending rows for a smoke test.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed every row even when the current vector is valid.",
    )
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")

    stats = embed_pending_rows(
        database_path=args.database,
        table_name=args.table,
        model_name=args.model,
        model_revision=args.model_revision,
        batch_size=args.batch_size,
        device=args.device,
        limit=args.limit,
        force=args.force,
    )
    print(
        "Embedding run: {selected} selected | {embedded} embedded | "
        "{failed} failed | {total} total rows".format(**stats)
    )
    if stats["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
