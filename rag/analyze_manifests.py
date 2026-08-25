"""Generate a readable analysis.txt report from ingestion manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from rag.source_config import (
        ANALYSIS_HISTORY_PATH,
        ANALYSIS_PATH,
        MANIFEST_ROOT,
        PROJECT_ROOT,
    )
except ModuleNotFoundError:
    from source_config import (
        ANALYSIS_HISTORY_PATH,
        ANALYSIS_PATH,
        MANIFEST_ROOT,
        PROJECT_ROOT,
    )


_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_CALLABLE_TYPES = {"constructor", "function", "method"}
_TOP_LIMIT = 20
_HISTORY_SCHEMA_VERSION = 1


def _token_count(text: str) -> int:
    return len(_TOKEN_RE.findall(text))


def _load_manifests(manifest_root: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(manifest_root.rglob("*.json")):
        manifests.append(json.loads(path.read_text(encoding="utf-8")))
    return manifests


def _without_summaries(value: Any) -> Any:
    """Remove LLM summaries so enrichment does not look like a source change."""
    if isinstance(value, dict):
        return {
            key: _without_summaries(item)
            for key, item in value.items()
            if key != "summary"
        }
    if isinstance(value, list):
        return [_without_summaries(item) for item in value]
    return value


def _manifest_inventory(manifests: list[dict[str, Any]]) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for manifest in manifests:
        relative_path = manifest["file"]["relative_path"]
        canonical = json.dumps(
            _without_summaries(manifest),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        inventory[relative_path] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return inventory


def manifest_inventory(manifests: list[dict[str, Any]]) -> dict[str, str]:
    """Return the source-derived fingerprint inventory used for change detection."""
    return _manifest_inventory(manifests)


def _load_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": _HISTORY_SCHEMA_VERSION,
            "inventory": {},
            "runs": [],
        }

    history = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(history, dict):
        raise ValueError(f"History state must be a JSON object: {path}")
    if history.get("schema_version") != _HISTORY_SCHEMA_VERSION:
        raise ValueError(f"Unsupported history schema in {path}")
    if not isinstance(history.get("inventory"), dict) or not isinstance(
        history.get("runs"), list
    ):
        raise ValueError(f"Invalid history state: {path}")
    return history


def load_history(path: Path = ANALYSIS_HISTORY_PATH) -> dict[str, Any]:
    """Load and validate the persisted manifest snapshot history."""
    return _load_history(path)


def latest_history_run(history: dict[str, Any]) -> dict[str, Any]:
    """Return the most recently recorded analysis run."""
    runs = history.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError(
            "No manifest analysis run exists. Run analyze_manifests.py after CocoIndex."
        )
    run = runs[-1]
    if not isinstance(run, dict):
        raise ValueError("The latest manifest analysis run is invalid")
    return run


def _create_history_run(
    previous_inventory: dict[str, str],
    current_inventory: dict[str, str],
    *,
    baseline: bool,
) -> dict[str, Any]:
    previous_paths = set(previous_inventory)
    current_paths = set(current_inventory)

    if baseline:
        added: list[str] = []
        modified: list[str] = []
        removed: list[str] = []
        unchanged = len(current_paths)
        kind = "baseline"
    else:
        added = sorted(current_paths - previous_paths)
        removed = sorted(previous_paths - current_paths)
        modified = sorted(
            path
            for path in current_paths & previous_paths
            if current_inventory[path] != previous_inventory[path]
        )
        unchanged = len(current_paths & previous_paths) - len(modified)
        kind = "changes_detected" if added or modified or removed else "no_changes"

    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="microseconds"),
        "kind": kind,
        "current_files": len(current_paths),
        "added": added,
        "modified": modified,
        "removed": removed,
        "unchanged": unchanged,
    }


def _history_lines(runs: list[dict[str, Any]]) -> list[str]:
    lines = [
        "Manifest snapshot history",
        "-------------------------",
        "Recorded whenever analyze_manifests runs after CocoIndex.",
        "",
    ]
    for run in reversed(runs):
        timestamp = run["timestamp"]
        kind = run["kind"]
        lines.append(f"{timestamp}  [{kind}]")
        if kind == "baseline":
            lines.append(f"  Baseline captured: {run['current_files']} files")
        else:
            lines.append(
                "  Current: {current} | Added: {added} | Modified: {modified} | "
                "Removed: {removed} | Unchanged: {unchanged}".format(
                    current=run["current_files"],
                    added=len(run["added"]),
                    modified=len(run["modified"]),
                    removed=len(run["removed"]),
                    unchanged=run["unchanged"],
                )
            )
            if kind == "no_changes":
                lines.append("  No manifest changes detected.")

        for label, key in (
            ("Added", "added"),
            ("Modified", "modified"),
            ("Removed", "removed"),
        ):
            paths = run.get(key, [])
            if paths:
                lines.append(f"  {label}:")
                lines.extend(f"    {path}" for path in paths)
        lines.append("")
    return lines


def _write_history(
    path: Path,
    inventory: dict[str, str],
    runs: list[dict[str, Any]],
) -> None:
    state = {
        "schema_version": _HISTORY_SCHEMA_VERSION,
        "inventory": inventory,
        "runs": runs,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _ranked_lines(
    title: str,
    rows: list[tuple[int, str]],
    value_label: str,
    limit: int = _TOP_LIMIT,
) -> list[str]:
    lines = [title, "-" * len(title)]
    if not rows:
        return [*lines, "None", ""]
    for value, label in sorted(rows, reverse=True)[:limit]:
        lines.append(f"{value:>8} {value_label}  {label}")
    lines.append("")
    return lines


def build_report(
    manifests: list[dict[str, Any]],
    history_runs: list[dict[str, Any]] | None = None,
) -> str:
    file_count = len(manifests)
    node_count = sum(len(manifest.get("nodes", [])) for manifest in manifests)
    chunk_count = sum(len(manifest.get("chunks", [])) for manifest in manifests)
    total_bytes = sum(manifest["file"]["size_bytes"] for manifest in manifests)
    total_tokens = sum(
        chunk["token_count_approx"]
        for manifest in manifests
        for chunk in manifest.get("chunks", [])
    )

    languages: Counter[str] = Counter()
    extensions: Counter[str] = Counter()
    source_kinds: Counter[str] = Counter()
    node_types: Counter[str] = Counter()
    files_with_nodes = 0
    files_without_nodes = 0
    files_with_zero_chunks = 0
    files_with_one_chunk = 0
    files_with_multiple_chunks = 0
    whole_file_chunks = 0
    chunks_without_nodes = 0
    chunks_with_one_node = 0
    chunks_with_multiple_nodes = 0
    nodes_without_chunks = 0

    files_by_bytes: list[tuple[int, str]] = []
    files_by_tokens: list[tuple[int, str]] = []
    files_by_nodes: list[tuple[int, str]] = []
    files_by_chunks: list[tuple[int, str]] = []
    chunks_by_tokens: list[tuple[int, str]] = []
    nodes_by_tokens: list[tuple[int, str]] = []
    split_callables: list[tuple[int, str]] = []
    multi_node_chunks: list[tuple[int, str]] = []
    per_file_sections: list[str] = []

    for manifest in sorted(
        manifests, key=lambda item: item["file"]["relative_path"]
    ):
        file_record = manifest["file"]
        nodes = manifest.get("nodes", [])
        chunks = manifest.get("chunks", [])
        relative_path = file_record["relative_path"]
        file_tokens = sum(chunk["token_count_approx"] for chunk in chunks)
        languages[file_record.get("language") or "none"] += 1
        extensions[file_record.get("extension") or "no extension"] += 1
        source_kinds[file_record["source_kind"]] += 1
        node_types.update(node["type"] for node in nodes)

        if nodes:
            files_with_nodes += 1
        else:
            files_without_nodes += 1
        if not chunks:
            files_with_zero_chunks += 1
        elif len(chunks) == 1:
            files_with_one_chunk += 1
        else:
            files_with_multiple_chunks += 1

        source_path = PROJECT_ROOT / relative_path
        source_text = (
            source_path.read_text(encoding="utf-8", errors="replace")
            if source_path.is_file()
            else None
        )
        is_whole_file_chunk = bool(
            source_text is not None
            and len(chunks) == 1
            and chunks[0]["text"].strip() == source_text.strip()
        )
        if is_whole_file_chunk:
            whole_file_chunks += 1

        files_by_bytes.append((file_record["size_bytes"], relative_path))
        files_by_tokens.append((file_tokens, relative_path))
        files_by_nodes.append((len(nodes), relative_path))
        files_by_chunks.append((len(chunks), relative_path))

        node_to_chunks: dict[str, set[int]] = defaultdict(set)
        for chunk in chunks:
            related_ids = set(chunk.get("related_node_ids", []))
            parent_id = chunk.get("parent_node_id")
            if parent_id:
                related_ids.add(parent_id)
            if not related_ids:
                chunks_without_nodes += 1
            elif len(related_ids) == 1:
                chunks_with_one_node += 1
            else:
                chunks_with_multiple_nodes += 1
                multi_node_chunks.append(
                    (
                        len(related_ids),
                        f"{chunk['chunk_id']} (lines {chunk['start_line']}-{chunk['end_line']})",
                    )
                )
            for node_id in related_ids:
                node_to_chunks[node_id].add(chunk["chunk_index"])
            chunks_by_tokens.append(
                (
                    chunk["token_count_approx"],
                    f"{chunk['chunk_id']} (lines {chunk['start_line']}-{chunk['end_line']})",
                )
            )

        for node in nodes:
            connected_chunks = sorted(node_to_chunks.get(node["node_id"], set()))
            if not connected_chunks:
                nodes_without_chunks += 1
            node_tokens = _token_count(node["text"])
            nodes_by_tokens.append(
                (
                    node_tokens,
                    f"{node['node_id']} (lines {node['start_line']}-{node['end_line']})",
                )
            )
            if node["type"] in _CALLABLE_TYPES and len(connected_chunks) > 1:
                split_callables.append(
                    (
                        len(connected_chunks),
                        f"{node['node_id']} -> chunks "
                        + ", ".join(f"{index:04d}" for index in connected_chunks),
                    )
                )

        per_file_sections.append(relative_path)
        per_file_sections.append("~" * len(relative_path))
        per_file_sections.append(
            "language={language} | bytes={bytes} | approx_tokens={tokens} | "
            "nodes={nodes} | chunks={chunks} | whole_file_chunk={whole}".format(
                language=file_record.get("language") or "none",
                bytes=file_record["size_bytes"],
                tokens=file_tokens,
                nodes=len(nodes),
                chunks=len(chunks),
                whole="yes" if is_whole_file_chunk else "no",
            )
        )
        if nodes:
            for node in nodes:
                indexes = sorted(node_to_chunks.get(node["node_id"], set()))
                chunk_labels = ", ".join(
                    f"chunk-{index:04d}" for index in indexes
                ) or "no chunks"
                per_file_sections.append(
                    f"  [{node['type']}] {node['qualified_name']} "
                    f"lines {node['start_line']}-{node['end_line']} -> {chunk_labels}"
                )
        else:
            per_file_sections.append("  nodes: none")
        per_file_sections.append("")

    lines = [
        "RAG INGESTION ANALYSIS",
        "======================",
        "",
        *_history_lines(history_runs or []),
        "Corpus totals",
        "-------------",
        f"Files: {file_count}",
        f"Nodes: {node_count}",
        f"Chunks: {chunk_count}",
        f"Source bytes: {total_bytes}",
        f"Approximate chunk tokens: {total_tokens}",
        f"Files with nodes: {files_with_nodes}",
        f"Files without nodes: {files_without_nodes}",
        f"Files with zero chunks: {files_with_zero_chunks}",
        f"Files with one chunk: {files_with_one_chunk}",
        f"Files with multiple chunks: {files_with_multiple_chunks}",
        f"Files represented by one complete-file chunk: {whole_file_chunks}",
        f"Chunks without related nodes: {chunks_without_nodes}",
        f"Chunks with one related node: {chunks_with_one_node}",
        f"Chunks with multiple related nodes: {chunks_with_multiple_nodes}",
        f"Nodes without connected chunks: {nodes_without_chunks}",
        "",
    ]

    for title, counter in (
        ("Files by language", languages),
        ("Files by extension", extensions),
        ("Files by source kind", source_kinds),
        ("Nodes by type", node_types),
    ):
        lines.extend([title, "-" * len(title)])
        for label, count in sorted(counter.items()):
            lines.append(f"{count:>8}  {label}")
        lines.append("")

    lines.extend(_ranked_lines("Largest source files", files_by_bytes, "bytes"))
    lines.extend(_ranked_lines("Files with most tokens", files_by_tokens, "tokens"))
    lines.extend(_ranked_lines("Files with most nodes", files_by_nodes, "nodes"))
    lines.extend(_ranked_lines("Files with most chunks", files_by_chunks, "chunks"))
    lines.extend(_ranked_lines("Largest chunks", chunks_by_tokens, "tokens"))
    lines.extend(_ranked_lines("Largest nodes/functions", nodes_by_tokens, "tokens"))
    lines.extend(
        _ranked_lines(
            "Functions represented by multiple chunks",
            split_callables,
            "chunks",
        )
    )
    lines.extend(
        _ranked_lines(
            "Chunks connected to multiple nodes",
            multi_node_chunks,
            "nodes",
        )
    )
    lines.extend(
        [
            "Per-file node and chunk mapping",
            "===============================",
            "",
            *per_file_sections,
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-root", type=Path, default=MANIFEST_ROOT)
    parser.add_argument("--output", type=Path, default=ANALYSIS_PATH)
    parser.add_argument(
        "--history",
        type=Path,
        help="History state path (default: .analysis_history.json beside output)",
    )
    args = parser.parse_args()

    manifests = _load_manifests(args.manifest_root)
    history_path = args.history or (
        ANALYSIS_HISTORY_PATH
        if args.output == ANALYSIS_PATH
        else args.output.parent / ".analysis_history.json"
    )
    history = _load_history(history_path)
    inventory = _manifest_inventory(manifests)
    runs = list(history["runs"])
    runs.append(
        _create_history_run(
            history["inventory"],
            inventory,
            baseline=not runs,
        )
    )
    report = build_report(manifests, runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    _write_history(history_path, inventory, runs)
    print(f"Wrote analysis for {len(manifests)} files to {args.output}")
    print(f"Updated manifest history at {history_path}")


if __name__ == "__main__":
    main()
