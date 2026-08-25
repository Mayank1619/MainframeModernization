"""Export the current LanceDB embedding table to one timestamped Parquet file."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import lancedb
import pyarrow.parquet as parquet

try:
    from rag.source_config import RAG_ROOT
    from rag.sync_embedding_table import DATABASE_PATH, TABLE_NAME
except ModuleNotFoundError:
    from source_config import RAG_ROOT
    from sync_embedding_table import DATABASE_PATH, TABLE_NAME


def export_embeddings(
    database_path: Path,
    table_name: str,
    output_path: Path | None = None,
) -> Path:
    database = lancedb.connect(database_path)
    if table_name not in set(database.list_tables().tables):
        raise FileNotFoundError(
            f"LanceDB table '{table_name}' does not exist at {database_path}"
        )

    table = database.open_table(table_name)
    rows = table.to_arrow()
    if rows.num_rows == 0:
        raise ValueError(f"LanceDB table '{table_name}' is empty")

    if output_path is None:
        timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        output_path = RAG_ROOT / f"embeddings_{timestamp}.parquet"
    elif output_path.suffix.lower() != ".parquet":
        output_path = output_path.with_suffix(".parquet")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    parquet.write_table(rows, output_path, compression="zstd")
    print(f"Exported {rows.num_rows} embedding rows to {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DATABASE_PATH)
    parser.add_argument("--table", default=TABLE_NAME)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path; defaults to rag/embeddings_<timestamp>.parquet",
    )
    args = parser.parse_args()

    export_embeddings(
        database_path=args.database,
        table_name=args.table,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
