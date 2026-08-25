"""Export the latest changed files and split nodes for AI summarization."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
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


DEFAULT_SINGLE_FILE_OUTPUT = RAG_ROOT / "output" / "single_chunk_files.json"
DEFAULT_MULTI_FILE_OUTPUT = (
    RAG_ROOT / "output" / "single_summary_across_all_chunks.json"
)
DEFAULT_NODE_OUTPUT = RAG_ROOT / "output" / "node_level_summary.json"
CALLABLE_NODE_TYPES = {"constructor", "function", "method"}
SUMMARY_INPUT_SCHEMA_VERSION = 1


def _line_count(text: str) -> int:
    return text.count("\n") + (0 if text.endswith("\n") or not text else 1)


def _load_manifests(manifest_root: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(manifest_root.rglob("*.json")):
        manifests.append(json.loads(path.read_text(encoding="utf-8")))
    return manifests


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _source_text(manifest: dict[str, Any]) -> str:
    file_record = manifest["file"]
    source_path = PROJECT_ROOT / file_record["relative_path"]
    if not source_path.is_file():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    text = source_path.read_text(encoding="utf-8", errors="replace")
    if len(text.encode("utf-8")) != file_record["size_bytes"]:
        raise ValueError(
            f"Source changed after manifest creation: {file_record['file_id']}. "
            "Run CocoIndex and analyze_manifests.py again."
        )
    if _line_count(text) != file_record["line_count"]:
        raise ValueError(
            f"Source line count changed after manifest creation: "
            f"{file_record['file_id']}. Run CocoIndex and "
            "analyze_manifests.py again."
        )
    for chunk in manifest.get("chunks", []):
        if chunk["text"] and chunk["text"] not in text:
            raise ValueError(
                f"Source no longer matches manifest chunks: {file_record['file_id']}. "
                "Run CocoIndex and analyze_manifests.py again."
            )
    return text


def _file_input(manifest: dict[str, Any], source_text: str) -> dict[str, str]:
    file_record = manifest["file"]
    return {
        "file_id": file_record["file_id"],
        "file_name": file_record["filename"],
        "full_file_code": source_text,
    }


def _connected_chunks(manifest: dict[str, Any]) -> dict[str, set[str]]:
    node_to_chunks: dict[str, set[str]] = defaultdict(set)
    for chunk in manifest.get("chunks", []):
        node_ids = set(chunk.get("related_node_ids", []))
        parent_node_id = chunk.get("parent_node_id")
        if parent_node_id:
            node_ids.add(parent_node_id)
        for node_id in node_ids:
            node_to_chunks[node_id].add(chunk["chunk_id"])
    return node_to_chunks


def build_summary_inputs(
    manifests: list[dict[str, Any]],
    selected_file_ids: set[str],
    *,
    analysis_run_timestamp: str,
    selection_mode: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    single_file_inputs: list[dict[str, str]] = []
    multi_file_inputs: list[dict[str, str]] = []
    node_inputs: list[dict[str, str]] = []
    node_file_ids: set[str] = set()

    for manifest in sorted(
        manifests,
        key=lambda item: item["file"]["relative_path"],
    ):
        file_record = manifest["file"]
        file_id = file_record["file_id"]
        if file_id not in selected_file_ids:
            continue

        source_text = _source_text(manifest)
        chunks = manifest.get("chunks", [])
        if not chunks:
            if source_text:
                raise ValueError(f"Nonempty source has zero chunks: {file_id}")
            continue

        file_input = _file_input(manifest, source_text)
        if len(chunks) == 1:
            single_file_inputs.append(file_input)
            continue

        multi_file_inputs.append(file_input)
        node_to_chunks = _connected_chunks(manifest)
        for node in manifest.get("nodes", []):
            node_id = node["node_id"]
            if node["type"] not in CALLABLE_NODE_TYPES:
                continue
            if len(node_to_chunks.get(node_id, set())) < 2:
                continue
            node_file_ids.add(file_id)
            node_inputs.append(
                {
                    "file_id": file_id,
                    "file_name": file_record["filename"],
                    "node_id": node_id,
                    "node_text": node["text"],
                }
            )

    common = {
        "schema_version": SUMMARY_INPUT_SCHEMA_VERSION,
        "analysis_run_timestamp": analysis_run_timestamp,
        "selection_mode": selection_mode,
    }
    single_payload = {
        **common,
        "file_count": len(single_file_inputs),
        "files": single_file_inputs,
    }
    multi_payload = {
        **common,
        "file_count": len(multi_file_inputs),
        "files": multi_file_inputs,
    }
    node_payload = {
        **common,
        "file_count": len(node_file_ids),
        "node_count": len(node_inputs),
        "nodes": node_inputs,
    }
    return single_payload, multi_payload, node_payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-root", type=Path, default=MANIFEST_ROOT)
    parser.add_argument("--history", type=Path, default=ANALYSIS_HISTORY_PATH)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export every nonempty manifest instead of only the latest changes.",
    )
    parser.add_argument(
        "--single-file-output",
        type=Path,
        default=DEFAULT_SINGLE_FILE_OUTPUT,
    )
    parser.add_argument(
        "--multi-file-output",
        type=Path,
        default=DEFAULT_MULTI_FILE_OUTPUT,
    )
    parser.add_argument("--node-output", type=Path, default=DEFAULT_NODE_OUTPUT)
    args = parser.parse_args()

    manifests = _load_manifests(args.manifest_root)
    history = load_history(args.history)
    latest_run = latest_history_run(history)
    if manifest_inventory(manifests) != history["inventory"]:
        raise ValueError(
            "Manifest history is stale. Run analyze_manifests.py after CocoIndex "
            "before exporting AI summary inputs."
        )

    current_file_ids = {
        manifest["file"]["file_id"] for manifest in manifests
    }
    if args.all:
        selected_file_ids = current_file_ids
        selection_mode = "all"
    else:
        selected_file_ids = set(latest_run.get("added", [])) | set(
            latest_run.get("modified", [])
        )
        missing = selected_file_ids - current_file_ids
        if missing:
            raise ValueError(
                "Latest added/modified files are missing from manifests: "
                f"{sorted(missing)[:5]}"
            )
        selection_mode = "latest_changes"

    single_payload, multi_payload, node_payload = build_summary_inputs(
        manifests,
        selected_file_ids,
        analysis_run_timestamp=latest_run["timestamp"],
        selection_mode=selection_mode,
    )
    _write_json(args.single_file_output, single_payload)
    _write_json(args.multi_file_output, multi_payload)
    _write_json(args.node_output, node_payload)

    print(
        f"Wrote {single_payload['file_count']} single-chunk files to "
        f"{args.single_file_output}"
    )
    print(
        f"Wrote {multi_payload['file_count']} multi-chunk files to "
        f"{args.multi_file_output}"
    )
    print(
        f"Wrote {node_payload['node_count']} split callable nodes from "
        f"{node_payload['file_count']} files to {args.node_output}"
    )


if __name__ == "__main__":
    main()
