"""Validate the readable source manifests after an ingestion run."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from rag.records import SCHEMA_VERSION
from rag.source_config import MANIFEST_ROOT, iter_source_files


def _line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _load_manifests(manifest_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    manifests: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(manifest_root.rglob("*.json")):
        try:
            manifests.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read manifest {path}: {exc}") from exc
    return manifests


def validate(manifest_root: Path) -> tuple[Counter[str], list[str]]:
    manifests = _load_manifests(manifest_root)
    selected_sources = dict(iter_source_files())
    errors: list[str] = []
    totals: Counter[str] = Counter()
    seen_file_ids: set[str] = set()
    seen_node_ids: set[str] = set()
    seen_chunk_ids: set[str] = set()
    manifest_paths: set[str] = set()

    for manifest_path, manifest in manifests:
        file_record = manifest["file"]
        nodes = manifest.get("nodes", [])
        chunks = manifest.get("chunks", [])
        relative_path = file_record["relative_path"]
        manifest_paths.add(relative_path)
        totals["files"] += 1
        totals["nodes"] += len(nodes)
        totals["chunks"] += len(chunks)
        totals["bytes"] += file_record["size_bytes"]
        totals["approx_tokens"] += sum(
            chunk["token_count_approx"] for chunk in chunks
        )

        if manifest.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"Wrong schema version: {relative_path}")

        expected_location = f"{relative_path}.json"
        actual_location = manifest_path.relative_to(manifest_root).as_posix()
        if actual_location != expected_location:
            errors.append(
                f"Wrong manifest location: {actual_location} != {expected_location}"
            )

        file_id = file_record["file_id"]
        if file_id != relative_path:
            errors.append(f"file_id is not the readable path: {relative_path}")
        if file_id in seen_file_ids:
            errors.append(f"Duplicate file_id: {file_id}")
        seen_file_ids.add(file_id)

        source_path = selected_sources.get(PurePosixPath(relative_path))
        if source_path is None:
            errors.append(f"Manifest has no selected source: {relative_path}")
            source_text = ""
        else:
            source_text = source_path.read_text(encoding="utf-8", errors="replace")
            if len(source_text.encode("utf-8")) != file_record["size_bytes"]:
                errors.append(f"Wrong file size: {relative_path}")
            if _line_count(source_text) != file_record["line_count"]:
                errors.append(f"Wrong file line count: {relative_path}")

        source_line_count = max(1, _line_count(source_text))
        local_node_ids = {node["node_id"] for node in nodes}
        nodes_by_id = {node["node_id"]: node for node in nodes}
        for node in nodes:
            node_id = node["node_id"]
            if node_id in seen_node_ids:
                errors.append(f"Duplicate node_id: {node_id}")
            seen_node_ids.add(node_id)
            if not node_id.startswith(f"{file_id}::"):
                errors.append(f"Node ID does not start with file_id: {node_id}")

            parent_id = node.get("parent_node_id")
            if parent_id and parent_id not in local_node_ids:
                errors.append(f"Orphan node parent: {relative_path} {node_id}")
            start, end = node["start_line"], node["end_line"]
            if not 1 <= start <= end <= source_line_count:
                errors.append(f"Invalid node line range: {relative_path} {node_id}")
            if parent_id in nodes_by_id:
                parent = nodes_by_id[parent_id]
                if not parent["start_line"] <= start <= end <= parent["end_line"]:
                    errors.append(f"Node outside parent: {relative_path} {node_id}")
            if node["text"] and node["text"] not in source_text:
                errors.append(f"Node text not found in source: {relative_path} {node_id}")

        expected_indexes = list(range(1, len(chunks) + 1))
        actual_indexes = [chunk["chunk_index"] for chunk in chunks]
        if actual_indexes != expected_indexes:
            errors.append(f"Chunk indexes are not contiguous: {relative_path}")

        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            if chunk_id in seen_chunk_ids:
                errors.append(f"Duplicate chunk_id: {chunk_id}")
            seen_chunk_ids.add(chunk_id)
            expected_chunk_id = f"{file_id}::chunk-{chunk['chunk_index']:04d}"
            if chunk_id != expected_chunk_id:
                errors.append(f"Unexpected chunk_id: {chunk_id}")

            parent_id = chunk.get("parent_node_id")
            if parent_id and parent_id not in local_node_ids:
                errors.append(f"Orphan chunk parent: {relative_path} {chunk_id}")
            if any(
                node_id not in local_node_ids
                for node_id in chunk.get("related_node_ids", [])
            ):
                errors.append(f"Orphan related node: {relative_path} {chunk_id}")

            start, end = chunk["start_line"], chunk["end_line"]
            if not 1 <= start <= end <= source_line_count:
                errors.append(f"Invalid chunk line range: {relative_path} {chunk_id}")
            if parent_id in nodes_by_id:
                parent = nodes_by_id[parent_id]
                if not parent["start_line"] <= start <= end <= parent["end_line"]:
                    errors.append(f"Chunk outside parent: {relative_path} {chunk_id}")
            if chunk["text"] and chunk["text"] not in source_text:
                errors.append(f"Chunk text not found in source: {relative_path} {chunk_id}")

    expected_paths = {path.as_posix() for path in selected_sources}
    for missing in sorted(expected_paths - manifest_paths):
        errors.append(f"Missing manifest: {missing}")

    print("Manifest totals:")
    for key in ("files", "nodes", "chunks", "bytes", "approx_tokens"):
        print(f"  {key:>14}: {totals[key]}")
    return totals, errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-root",
        type=Path,
        default=MANIFEST_ROOT,
        help=f"Manifest directory (default: {MANIFEST_ROOT})",
    )
    args = parser.parse_args()
    _, errors = validate(args.manifest_root)
    if errors:
        print(f"\nValidation failed with {len(errors)} error(s):")
        for error in errors[:50]:
            print(f"  - {error}")
        raise SystemExit(1)
    print("\nValidation passed.")


if __name__ == "__main__":
    main()
