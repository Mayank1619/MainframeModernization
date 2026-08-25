"""Upsert AI-enriched manifests into the complete embedding-input snapshot."""

from __future__ import annotations

import argparse
import copy
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from rag.ai_summary_input import SUMMARY_INPUT_SCHEMA_VERSION
    from rag.analyze_manifests import (
        latest_history_run,
        load_history,
        manifest_inventory,
    )
    from rag.source_config import (
        ANALYSIS_HISTORY_PATH,
        MANIFEST_ROOT,
        PROJECT_ROOT,
        RAG_ROOT,
    )
except ModuleNotFoundError:
    from ai_summary_input import SUMMARY_INPUT_SCHEMA_VERSION
    from analyze_manifests import (
        latest_history_run,
        load_history,
        manifest_inventory,
    )
    from source_config import (
        ANALYSIS_HISTORY_PATH,
        MANIFEST_ROOT,
        PROJECT_ROOT,
        RAG_ROOT,
    )


OUTPUT_ROOT = RAG_ROOT / "input_embeddings"
SINGLE_FILE_SUMMARIES = RAG_ROOT / "output" / "single_chunk_files_summaries.csv"
MULTI_FILE_SUMMARIES = RAG_ROOT / "output" / "multi_chunk_file_summaries.csv"
NODE_SUMMARIES = RAG_ROOT / "output" / "node_level_summaries.csv"
SINGLE_FILE_SOURCES = RAG_ROOT / "output" / "single_chunk_files.json"
MULTI_FILE_SOURCES = RAG_ROOT / "output" / "single_summary_across_all_chunks.json"
NODE_SOURCES = RAG_ROOT / "output" / "node_level_summary.json"

FILE_SUMMARY_COLUMNS = ["file_id", "file_name", "ai_summary"]
NODE_SUMMARY_COLUMNS = ["file_id", "file_name", "node_id", "ai_summary"]


@dataclass(frozen=True)
class SummaryRun:
    timestamp: str
    selection_mode: str


@dataclass(frozen=True)
class FileSummary:
    file_id: str
    filename: str
    summary: str
    expected_chunk_kind: str
    source_text: str


@dataclass(frozen=True)
class NodeSummary:
    file_id: str
    filename: str
    node_id: str
    summary: str
    source_text: str


def _read_csv(path: Path, expected_columns: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Summary CSV does not exist: {path}. Run generate_ai_summaries.py first."
        )
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_columns:
            raise ValueError(
                f"Expected CSV columns {expected_columns} in {path}, "
                f"got {reader.fieldnames}"
            )
        rows = list(reader)

    for row_number, row in enumerate(rows, start=2):
        for column in expected_columns:
            row[column] = row[column].strip()
            if not row[column]:
                raise ValueError(f"Missing {column} in {path} row {row_number}")
    return rows


def _load_source_payload(path: Path, collection_key: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Summary source does not exist: {path}. Run ai_summary_input.py first."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SUMMARY_INPUT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported summary input schema in {path}")
    if not isinstance(payload.get(collection_key), list):
        raise ValueError(f"Expected a {collection_key} list in {path}")
    return payload


def _summary_run(payload: dict[str, Any], path: Path) -> SummaryRun:
    timestamp = payload.get("analysis_run_timestamp")
    selection_mode = payload.get("selection_mode")
    if not isinstance(timestamp, str) or not timestamp:
        raise ValueError(f"Missing analysis_run_timestamp in {path}")
    if selection_mode not in {"latest_changes", "all"}:
        raise ValueError(f"Invalid selection_mode in {path}: {selection_mode}")
    return SummaryRun(timestamp=timestamp, selection_mode=selection_mode)


def _load_file_sources(
    path: Path,
) -> tuple[dict[str, dict[str, str]], SummaryRun]:
    payload = _load_source_payload(path, "files")
    files = payload["files"]
    if payload.get("file_count") != len(files):
        raise ValueError(f"file_count does not match files in {path}")

    sources: dict[str, dict[str, str]] = {}
    for item in files:
        file_id = item["file_id"]
        if file_id in sources:
            raise ValueError(f"Duplicate file_id in {path}: {file_id}")
        sources[file_id] = item
    return sources, _summary_run(payload, path)


def _load_file_summary_group(
    csv_path: Path,
    source_path: Path,
    expected_chunk_kind: str,
) -> tuple[dict[str, FileSummary], SummaryRun]:
    rows = _read_csv(csv_path, FILE_SUMMARY_COLUMNS)
    sources, run = _load_file_sources(source_path)
    row_ids = {row["file_id"] for row in rows}
    if len(row_ids) != len(rows):
        raise ValueError(f"Duplicate file_id in {csv_path}")
    if row_ids != set(sources):
        raise ValueError(f"File IDs differ between {csv_path} and {source_path}")

    summaries: dict[str, FileSummary] = {}
    for row in rows:
        file_id = row["file_id"]
        source = sources[file_id]
        if row["file_name"] != source["file_name"]:
            raise ValueError(f"Filename mismatch for {file_id}")
        summaries[file_id] = FileSummary(
            file_id=file_id,
            filename=row["file_name"],
            summary=row["ai_summary"],
            expected_chunk_kind=expected_chunk_kind,
            source_text=source["full_file_code"],
        )
    return summaries, run


def _load_node_summaries(
    csv_path: Path,
    source_path: Path,
) -> tuple[dict[str, NodeSummary], SummaryRun]:
    rows = _read_csv(csv_path, NODE_SUMMARY_COLUMNS)
    payload = _load_source_payload(source_path, "nodes")
    nodes = payload["nodes"]
    if payload.get("node_count") != len(nodes):
        raise ValueError(f"node_count does not match nodes in {source_path}")

    sources: dict[str, dict[str, str]] = {}
    for node in nodes:
        node_id = node["node_id"]
        if node_id in sources:
            raise ValueError(f"Duplicate node_id in {source_path}: {node_id}")
        sources[node_id] = node

    row_ids = {row["node_id"] for row in rows}
    if len(row_ids) != len(rows):
        raise ValueError(f"Duplicate node_id in {csv_path}")
    if row_ids != set(sources):
        raise ValueError(f"Node IDs differ between {csv_path} and {source_path}")

    summaries: dict[str, NodeSummary] = {}
    for row in rows:
        node_id = row["node_id"]
        source = sources[node_id]
        if row["file_id"] != source["file_id"]:
            raise ValueError(f"File ID mismatch for node {node_id}")
        if row["file_name"] != source["file_name"]:
            raise ValueError(f"Filename mismatch for node {node_id}")
        summaries[node_id] = NodeSummary(
            file_id=row["file_id"],
            filename=row["file_name"],
            node_id=node_id,
            summary=row["ai_summary"],
            source_text=source["node_text"],
        )
    return summaries, _summary_run(payload, source_path)


def _load_manifests(manifest_root: Path) -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(manifest_root.rglob("*.json"))
    ]


def _line_count(text: str) -> int:
    return text.count("\n") + (0 if text.endswith("\n") or not text else 1)


def _validate_source_matches_manifest(
    manifest: dict[str, Any],
    source_text: str,
) -> None:
    file_record = manifest["file"]
    if len(source_text.encode("utf-8")) != file_record["size_bytes"]:
        raise ValueError(
            f"Source changed after manifest creation: {file_record['file_id']}"
        )
    if _line_count(source_text) != file_record["line_count"]:
        raise ValueError(
            "Source line count changed after manifest creation: "
            f"{file_record['file_id']}"
        )
    for chunk in manifest.get("chunks", []):
        if chunk["text"] and chunk["text"] not in source_text:
            raise ValueError(
                f"Source no longer matches manifest chunks: {file_record['file_id']}"
            )


def _flat_output_name(file_id: str) -> str:
    name = f"file_{file_id.replace('/', '__')}.json"
    if len(name.encode("utf-8")) > 255:
        raise ValueError(f"Flattened filename exceeds 255 bytes: {file_id}")
    return name


def _embedding_text(
    file_summary: str,
    node_summaries: list[tuple[str, str]],
    code: str,
) -> str:
    sections = [f"File summary: {file_summary}"]
    sections.extend(
        f"Node summary [{node_name}]: {summary}"
        for node_name, summary in node_summaries
    )
    sections.append(f"Code:\n{code}")
    return "\n\n".join(sections)


def _build_embedding_manifest(
    manifest: dict[str, Any],
    file_summary: FileSummary,
    node_summaries: dict[str, NodeSummary],
) -> tuple[dict[str, Any], int, int]:
    enriched = copy.deepcopy(manifest)
    enriched["file"]["summary"] = file_summary.summary
    nodes_by_id = {node["node_id"]: node for node in enriched.get("nodes", [])}

    summaries_for_file = {
        node_id: summary
        for node_id, summary in node_summaries.items()
        if summary.file_id == file_summary.file_id
    }
    node_to_chunks: dict[str, set[str]] = defaultdict(set)
    for chunk in enriched.get("chunks", []):
        related_ids = set(chunk.get("related_node_ids", []))
        parent_id = chunk.get("parent_node_id")
        if parent_id:
            related_ids.add(parent_id)
        for node_id in related_ids:
            node_to_chunks[node_id].add(chunk["chunk_id"])

    for node_id, summary in summaries_for_file.items():
        node = nodes_by_id.get(node_id)
        if node is None:
            raise ValueError(f"Node no longer exists in manifest: {node_id}")
        if node["text"] != summary.source_text:
            raise ValueError(f"Node changed since it was summarized: {node_id}")
        if len(node_to_chunks.get(node_id, set())) < 2:
            raise ValueError(f"Node no longer spans multiple chunks: {node_id}")
        node["summary"] = summary.summary

    chunks_with_node_summaries = 0
    node_chunk_attachments = 0
    for chunk in enriched.get("chunks", []):
        related_ids = set(chunk.get("related_node_ids", []))
        parent_id = chunk.get("parent_node_id")
        if parent_id:
            related_ids.add(parent_id)
        relevant = [
            (
                nodes_by_id[node_id]["qualified_name"],
                summaries_for_file[node_id].summary,
            )
            for node_id in summaries_for_file
            if node_id in related_ids
        ]
        if relevant:
            chunks_with_node_summaries += 1
            node_chunk_attachments += len(relevant)
        chunk["embedding_text"] = _embedding_text(
            file_summary.summary,
            relevant,
            chunk["text"],
        )
    return enriched, chunks_with_node_summaries, node_chunk_attachments


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def create_embedding_inputs(
    manifest_root: Path,
    output_root: Path,
    history_path: Path,
    single_file_summaries: Path,
    multi_file_summaries: Path,
    node_summary_csv: Path,
    single_file_sources: Path,
    multi_file_sources: Path,
    node_sources: Path,
) -> dict[str, int]:
    single_summaries, single_run = _load_file_summary_group(
        single_file_summaries,
        single_file_sources,
        "single",
    )
    multi_summaries, multi_run = _load_file_summary_group(
        multi_file_summaries,
        multi_file_sources,
        "multiple",
    )
    node_summaries, node_run = _load_node_summaries(
        node_summary_csv,
        node_sources,
    )
    if len({single_run, multi_run, node_run}) != 1:
        raise ValueError(
            "Summary inputs came from different exports. Run ai_summary_input.py "
            "and generate_ai_summaries.py again."
        )
    summary_run = single_run

    duplicate_file_ids = set(single_summaries) & set(multi_summaries)
    if duplicate_file_ids:
        raise ValueError(f"File summaries overlap: {sorted(duplicate_file_ids)[:5]}")
    file_summaries = {**single_summaries, **multi_summaries}
    if not {summary.file_id for summary in node_summaries.values()} <= set(
        multi_summaries
    ):
        raise ValueError("Node summaries reference files without multi-chunk summaries")

    manifests = _load_manifests(manifest_root)
    manifests_by_id: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        file_id = manifest["file"]["file_id"]
        if file_id in manifests_by_id:
            raise ValueError(f"Duplicate manifest file_id: {file_id}")
        manifests_by_id[file_id] = manifest

    history = load_history(history_path)
    latest_run = latest_history_run(history)
    if manifest_inventory(manifests) != history["inventory"]:
        raise ValueError(
            "Manifest history is stale. Run analyze_manifests.py after CocoIndex."
        )
    if summary_run.timestamp != latest_run["timestamp"]:
        raise ValueError(
            "Summary files do not belong to the latest analysis run. "
            "Regenerate the summary inputs and summaries."
        )

    if summary_run.selection_mode == "all":
        selected_file_ids = set(manifests_by_id)
    else:
        selected_file_ids = set(latest_run.get("added", [])) | set(
            latest_run.get("modified", [])
        )
    expected_summary_ids = {
        file_id
        for file_id in selected_file_ids
        if file_id in manifests_by_id and manifests_by_id[file_id].get("chunks", [])
    }
    if set(file_summaries) != expected_summary_ids:
        raise ValueError(
            "Summary files do not exactly match the selected nonempty manifests. "
            "Run ai_summary_input.py and generate_ai_summaries.py again."
        )

    outputs: dict[str, dict[str, Any]] = {}
    total_chunks = 0
    chunks_with_node_summaries = 0
    node_chunk_attachments = 0
    for file_id, file_summary in sorted(file_summaries.items()):
        source_path = PROJECT_ROOT / file_id
        current_source = source_path.read_text(encoding="utf-8", errors="replace")
        if current_source != file_summary.source_text:
            raise ValueError(
                f"Source changed since its summary input was exported: {file_id}"
            )

        manifest = manifests_by_id[file_id]
        _validate_source_matches_manifest(manifest, current_source)
        file_record = manifest["file"]
        chunks = manifest.get("chunks", [])
        if file_record["filename"] != file_summary.filename:
            raise ValueError(f"Manifest filename mismatch for {file_id}")
        if file_summary.expected_chunk_kind == "single" and len(chunks) != 1:
            raise ValueError(f"Expected one chunk for {file_id}, got {len(chunks)}")
        if file_summary.expected_chunk_kind == "multiple" and len(chunks) <= 1:
            raise ValueError(f"Expected multiple chunks for {file_id}, got {len(chunks)}")

        enriched, node_chunks, attachments = _build_embedding_manifest(
            manifest,
            file_summary,
            node_summaries,
        )
        output_name = _flat_output_name(file_id)
        if output_name in outputs:
            raise ValueError(f"Flattened filename collision: {output_name}")
        outputs[output_name] = enriched
        total_chunks += len(chunks)
        chunks_with_node_summaries += node_chunks
        node_chunk_attachments += attachments

    output_root.mkdir(parents=True, exist_ok=True)
    removed_output_files = 0
    if summary_run.selection_mode == "all":
        expected_names = {_flat_output_name(file_id) for file_id in expected_summary_ids}
        delete_paths = [
            path for path in output_root.glob("*.json") if path.name not in expected_names
        ]
    else:
        delete_file_ids = set(latest_run.get("removed", [])) | (
            selected_file_ids - expected_summary_ids
        )
        delete_paths = [
            output_root / _flat_output_name(file_id) for file_id in delete_file_ids
        ]
    for path in delete_paths:
        if path.is_file():
            path.unlink()
            removed_output_files += 1

    for output_name, payload in outputs.items():
        _write_json(output_root / output_name, payload)

    return {
        "files_updated": len(outputs),
        "files_removed": removed_output_files,
        "chunks_updated": total_chunks,
        "node_summaries": len(node_summaries),
        "chunks_with_node_summaries": chunks_with_node_summaries,
        "node_chunk_attachments": node_chunk_attachments,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-root", type=Path, default=MANIFEST_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--history", type=Path, default=ANALYSIS_HISTORY_PATH)
    parser.add_argument("--single-file-summaries", type=Path, default=SINGLE_FILE_SUMMARIES)
    parser.add_argument("--multi-file-summaries", type=Path, default=MULTI_FILE_SUMMARIES)
    parser.add_argument("--node-summaries", type=Path, default=NODE_SUMMARIES)
    parser.add_argument("--single-file-sources", type=Path, default=SINGLE_FILE_SOURCES)
    parser.add_argument("--multi-file-sources", type=Path, default=MULTI_FILE_SOURCES)
    parser.add_argument("--node-sources", type=Path, default=NODE_SOURCES)
    args = parser.parse_args()

    stats = create_embedding_inputs(
        manifest_root=args.manifest_root,
        output_root=args.output,
        history_path=args.history,
        single_file_summaries=args.single_file_summaries,
        multi_file_summaries=args.multi_file_summaries,
        node_summary_csv=args.node_summaries,
        single_file_sources=args.single_file_sources,
        multi_file_sources=args.multi_file_sources,
        node_sources=args.node_sources,
    )
    print(
        "Embedding inputs: {files_updated} files updated | "
        "{chunks_updated} chunks updated | {files_removed} files removed".format(
            **stats
        )
    )
    print(
        "Attached {node_summaries} node summaries to "
        "{chunks_with_node_summaries} relevant chunks "
        "({node_chunk_attachments} node/chunk links)".format(**stats)
    )


if __name__ == "__main__":
    main()
