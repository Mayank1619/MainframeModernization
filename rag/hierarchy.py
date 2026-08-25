"""Extract stable source hierarchy with CocoIndex's Tree-sitter engine."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from cocoindex.ops.code import CodeMatch, CodePattern, CodeSource

from rag.records import HierarchyNodeRecord


_WHITESPACE_RE = re.compile(r"\s+")
_COPYBOOK_ENTRY_RE = re.compile(
    r"^[ \t]*(?:\d{6}[ \t]+)?(\d{2}|66|77|88)[ \t]+([A-Z][A-Z0-9-]*)",
    re.IGNORECASE,
)
_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")


@dataclass(frozen=True)
class _PatternSpec:
    pattern: str
    kind: str
    match_kinds: frozenset[str]
    name_capture: str | None = "NAME"
    args_capture: str | None = None
    return_capture: str | None = None


@dataclass
class _Candidate:
    kind: str
    name: str
    signature: str | None
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int
    name_start_byte: int
    parent_index: int | None = None
    node_id: str = ""
    qualified_name: str = ""


_CLASS_KINDS = frozenset({"class_declaration", "abstract_class_declaration"})
_FUNCTION_KINDS = frozenset(
    {"function_declaration", "generator_function_declaration"}
)
_METHOD_KINDS = frozenset(
    {
        "abstract_method_signature",
        "constructor_declaration",
        "method_definition",
        "method_signature",
    }
)
_JAVA_CALLABLE_KINDS = frozenset(
    {"constructor_declaration", "method_declaration"}
)
_VARIABLE_FUNCTION_KINDS = frozenset(
    {"lexical_declaration", "variable_declaration"}
)

_PATTERN_SPECS: dict[str, tuple[_PatternSpec, ...]] = {
    "java": (
        _PatternSpec(r"class \NAME \BODY", "class", _CLASS_KINDS),
        _PatternSpec(
            r"class \NAME extends \BASE implements \IMPLEMENTS \BODY",
            "class",
            _CLASS_KINDS,
        ),
        _PatternSpec(
            r"class \NAME extends \BASE \BODY", "class", _CLASS_KINDS
        ),
        _PatternSpec(
            r"class \NAME implements \IMPLEMENTS \BODY", "class", _CLASS_KINDS
        ),
        _PatternSpec(
            r"interface \NAME \BODY",
            "interface",
            frozenset({"interface_declaration"}),
        ),
        _PatternSpec(
            r"interface \NAME extends \BASES \BODY",
            "interface",
            frozenset({"interface_declaration"}),
        ),
        _PatternSpec(r"enum \NAME \BODY", "enum", frozenset({"enum_declaration"})),
        _PatternSpec(
            r"enum \NAME implements \IMPLEMENTS \BODY",
            "enum",
            frozenset({"enum_declaration"}),
        ),
        _PatternSpec(
            r"record \NAME(\(ARGS*\)) \BODY",
            "record",
            frozenset({"record_declaration"}),
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"@interface \NAME \BODY",
            "annotation",
            frozenset({"annotation_type_declaration"}),
        ),
        _PatternSpec(
            r"\TYPE \NAME(\(ARGS*\)) \BODY",
            "method",
            _JAVA_CALLABLE_KINDS,
            args_capture="ARGS",
            return_capture="TYPE",
        ),
        _PatternSpec(
            r"\NAME(\(ARGS*\)) \BODY",
            "method",
            _JAVA_CALLABLE_KINDS,
            args_capture="ARGS",
        ),
    ),
    "javascript": (
        _PatternSpec(r"class \NAME \BODY", "class", _CLASS_KINDS),
        _PatternSpec(r"class \NAME \HERITAGE \BODY", "class", _CLASS_KINDS),
        _PatternSpec(
            r"function \NAME(\(ARGS*\)) \BODY",
            "function",
            _FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"function* \NAME(\(ARGS*\)) \BODY",
            "function",
            _FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"\NAME(\(ARGS*\)) \BODY",
            "method",
            _METHOD_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"const \NAME = (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"let \NAME = (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"const \NAME = async (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"let \NAME = async (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"const \NAME = \ARG => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARG",
        ),
        _PatternSpec(
            r"let \NAME = \ARG => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARG",
        ),
    ),
    "typescript": (
        _PatternSpec(r"class \NAME \BODY", "class", _CLASS_KINDS),
        _PatternSpec(r"class \NAME \HERITAGE \BODY", "class", _CLASS_KINDS),
        _PatternSpec(
            r"interface \NAME \BODY",
            "interface",
            frozenset({"interface_declaration"}),
        ),
        _PatternSpec(
            r"interface \NAME \HERITAGE \BODY",
            "interface",
            frozenset({"interface_declaration"}),
        ),
        _PatternSpec(r"enum \NAME \BODY", "enum", frozenset({"enum_declaration"})),
        _PatternSpec(
            r"type \NAME = \VALUE",
            "type_alias",
            frozenset({"type_alias_declaration"}),
        ),
        _PatternSpec(
            r"function \NAME(\(ARGS*\)): \TYPE \BODY",
            "function",
            _FUNCTION_KINDS,
            args_capture="ARGS",
            return_capture="TYPE",
        ),
        _PatternSpec(
            r"function \NAME(\(ARGS*\)) \BODY",
            "function",
            _FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"\NAME(\(ARGS*\)): \TYPE \BODY",
            "method",
            _METHOD_KINDS,
            args_capture="ARGS",
            return_capture="TYPE",
        ),
        _PatternSpec(
            r"\NAME(\(ARGS*\)) \BODY",
            "method",
            _METHOD_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"const \NAME = (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"let \NAME = (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"const \NAME = async (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"let \NAME = async (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
        ),
        _PatternSpec(
            r"const \NAME: \TYPE = (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
            return_capture="TYPE",
        ),
        _PatternSpec(
            r"const \NAME: \TYPE = async (\(ARGS*\)) => \BODY",
            "function",
            _VARIABLE_FUNCTION_KINDS,
            args_capture="ARGS",
            return_capture="TYPE",
        ),
    ),
    "html": (
        _PatternSpec(
            r"<script>\BODY</script>",
            "script",
            frozenset({"script_element"}),
            name_capture=None,
        ),
    ),
}
_PATTERN_SPECS["tsx"] = _PATTERN_SPECS["typescript"]


def _compact(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def _capture_text(match: CodeMatch, name: str | None) -> str | None:
    if name is None:
        return None
    chunks = match.captures.get(name)
    if not chunks:
        return None
    return _compact(" ".join(chunk.text for chunk in chunks))


def _capture_start(match: CodeMatch, name: str | None) -> int:
    if name is None:
        return match.chunks[0].start.byte_offset
    chunks = match.captures.get(name)
    if not chunks:
        return match.chunks[0].start.byte_offset
    return chunks[0].start.byte_offset


@lru_cache(maxsize=None)
def _compiled_pattern(language: str, pattern: str) -> CodePattern:
    return CodePattern(pattern, language=language, min_len=1)


def _code_candidates(text: str, language: str) -> list[_Candidate]:
    source = CodeSource(text, language=language)
    deduplicated: dict[tuple[str, str, int], _Candidate] = {}
    anonymous_counts: Counter[str] = Counter()

    for spec in _PATTERN_SPECS.get(language, ()):
        pattern = _compiled_pattern(language, spec.pattern)
        for match in pattern.match_source(source):
            if match.kind not in spec.match_kinds or not match.chunks:
                continue

            chunk = match.chunks[0]
            name = _capture_text(match, spec.name_capture)
            if not name:
                anonymous_counts[spec.kind] += 1
                name = f"inline-{spec.kind}-{anonymous_counts[spec.kind]}"
            args = _capture_text(match, spec.args_capture)
            return_type = _capture_text(match, spec.return_capture)
            if match.kind == "constructor_declaration":
                return_type = None
            signature = f"{name}({args or ''})" if spec.args_capture else None
            if signature and return_type:
                signature += f" -> {return_type}"

            candidate = _Candidate(
                kind=(
                    "constructor"
                    if match.kind == "constructor_declaration"
                    else spec.kind
                ),
                name=name,
                signature=signature,
                start_byte=chunk.start.byte_offset,
                end_byte=chunk.end.byte_offset,
                start_line=chunk.start.line,
                end_line=chunk.end.line,
                name_start_byte=_capture_start(match, spec.name_capture),
            )
            key = (candidate.kind, candidate.name, candidate.name_start_byte)
            previous = deduplicated.get(key)
            if previous is None or (
                candidate.end_byte - candidate.start_byte
                > previous.end_byte - previous.start_byte
            ):
                deduplicated[key] = candidate

    return list(deduplicated.values())


def _line_candidates(text: str, language: str) -> list[_Candidate]:
    source = text.encode("utf-8")
    source_line_count = max(1, len(source.splitlines()))
    candidates: list[_Candidate] = []
    level_stack: list[tuple[int, int]] = []
    offset = 0

    for line_number, line in enumerate(source.splitlines(keepends=True), start=1):
        decoded = line.decode("utf-8", errors="replace")
        if language == "markdown":
            match = _MARKDOWN_HEADING_RE.match(decoded)
            if match is None:
                offset += len(line)
                continue
            level = len(match.group(1))
            name = match.group(2).strip()
            kind = "section"
            signature = f"heading {level}"
        else:
            match = _COPYBOOK_ENTRY_RE.match(decoded)
            if match is None:
                offset += len(line)
                continue
            level = int(match.group(1))
            name = match.group(2).upper()
            kind = "copybook_field"
            signature = f"level {level:02d}"

        while level_stack and level_stack[-1][0] >= level:
            _, completed_index = level_stack.pop()
            candidates[completed_index].end_byte = offset
            candidates[completed_index].end_line = max(
                candidates[completed_index].start_line, line_number - 1
            )

        parent_index = level_stack[-1][1] if level_stack else None
        if language == "cobol" and level in {66, 77}:
            parent_index = None
        is_standalone_copybook_level = (
            language == "cobol" and level in {66, 77, 88}
        )
        candidates.append(
            _Candidate(
                kind=kind,
                name=name,
                signature=signature,
                start_byte=offset,
                end_byte=(
                    offset + len(line)
                    if is_standalone_copybook_level
                    else len(source)
                ),
                start_line=line_number,
                end_line=(
                    line_number
                    if is_standalone_copybook_level
                    else max(line_number, source_line_count)
                ),
                name_start_byte=offset,
                parent_index=parent_index,
            )
        )
        index = len(candidates) - 1
        if not is_standalone_copybook_level:
            level_stack.append((level, index))
        offset += len(line)

    return candidates


def _assign_parents(candidates: list[_Candidate]) -> None:
    ordered = sorted(
        range(len(candidates)),
        key=lambda index: (
            candidates[index].start_byte,
            -candidates[index].end_byte,
            candidates[index].kind,
            candidates[index].name,
        ),
    )
    stack: list[int] = []
    for index in ordered:
        candidate = candidates[index]
        if candidate.parent_index is not None:
            continue
        while stack:
            parent = candidates[stack[-1]]
            if (
                parent.start_byte <= candidate.start_byte
                and candidate.end_byte <= parent.end_byte
                and (parent.start_byte, parent.end_byte)
                != (candidate.start_byte, candidate.end_byte)
            ):
                break
            stack.pop()
        candidate.parent_index = stack[-1] if stack else None
        stack.append(index)


def _to_records(
    file_id: str, text: str, candidates: list[_Candidate]
) -> list[HierarchyNodeRecord]:
    source_lines = text.splitlines(keepends=True)
    _assign_parents(candidates)
    occurrences: Counter[str] = Counter()

    def populate_identity(index: int) -> None:
        candidate = candidates[index]
        if candidate.node_id:
            return
        if candidate.parent_index is not None:
            populate_identity(candidate.parent_index)
            parent_name = candidates[candidate.parent_index].qualified_name
            candidate.qualified_name = f"{parent_name}.{candidate.name}"
        else:
            candidate.qualified_name = candidate.name
        base_node_id = f"{file_id}::{candidate.kind}::{candidate.qualified_name}"
        if candidate.signature:
            base_node_id = f"{base_node_id}::{candidate.signature}"
        occurrence = occurrences[base_node_id]
        occurrences[base_node_id] += 1
        candidate.node_id = (
            base_node_id if occurrence == 0 else f"{base_node_id}::{occurrence + 1}"
        )

    for index in range(len(candidates)):
        populate_identity(index)

    records = [
        HierarchyNodeRecord(
            node_id=candidate.node_id,
            file_id=file_id,
            parent_node_id=(
                candidates[candidate.parent_index].node_id
                if candidate.parent_index is not None
                else None
            ),
            kind=candidate.kind,
            name=candidate.name,
            qualified_name=candidate.qualified_name,
            signature=candidate.signature,
            start_byte=candidate.start_byte,
            end_byte=candidate.end_byte,
            start_line=candidate.start_line,
            end_line=candidate.end_line,
            text="".join(source_lines[candidate.start_line - 1 : candidate.end_line]),
        )
        for candidate in candidates
    ]
    records.sort(key=lambda node: (node.start_byte, -node.end_byte, node.node_id))
    return records


def extract_hierarchy(
    *,
    file_id: str,
    text: str,
    language: str | None,
) -> list[HierarchyNodeRecord]:
    """Extract classes, functions, sections, and copybook fields for one file."""
    if not text or language is None:
        return []
    if language in _PATTERN_SPECS:
        candidates = _code_candidates(text, language)
    elif language in {"cobol", "markdown"}:
        candidates = _line_candidates(text, language)
    else:
        candidates = []
    return _to_records(file_id, text, candidates)
