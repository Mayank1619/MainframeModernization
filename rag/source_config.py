"""Source selection and language configuration for the RAG ingestion pipeline."""

from __future__ import annotations

from collections.abc import Iterator
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAG_ROOT = Path(__file__).resolve().parent
MANIFEST_ROOT = RAG_ROOT / "output" / "manifests"
ANALYSIS_PATH = RAG_ROOT / "output" / "analysis.txt"
ANALYSIS_HISTORY_PATH = RAG_ROOT / "output" / ".analysis_history.json"
COCOINDEX_DB_PATH = RAG_ROOT / "cocoindex.db"
SOURCE_ROOTS = (
    PurePosixPath("frontend"),
    PurePosixPath("backend/api"),
)

SUPPORTED_SUFFIXES = {
    ".css",
    ".cpy",
    ".dai",
    ".gradle",
    ".html",
    ".java",
    ".js",
    ".json",
    ".md",
    ".properties",
    ".sql",
    ".ts",
    ".tsx",
    ".xml",
    ".yaml",
    ".yml",
}

SUPPORTED_FILENAMES = {
    ".gitkeep",
    ".gitignore",
    ".openapi-generator-ignore",
}

EXCLUDED_PATTERNS = [
    "**/node_modules/**",
    "**/target/**",
    "**/build/**",
    "**/dist/**",
    "**/package-lock.json",
    "**/.DS_Store",
    "frontend/legacy-static/css/carbon-styles.min.css",
    "frontend/legacy-static/js/carbon-web-components.min.js",
    "frontend/app/src/assets/**",
    "**/*.class",
    "**/*.jar",
    "**/*.db",
    "**/*.svg",
    "**/*.png",
]

LANGUAGE_BY_SUFFIX = {
    ".css": "css",
    ".cpy": "cobol",
    ".dai": "xml",
    ".gradle": "groovy",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".md": "markdown",
    ".properties": "properties",
    ".sql": "sql",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def is_supported(relative_path: PurePosixPath) -> bool:
    """Return whether a selected source file is text we intentionally ingest."""
    return (
        relative_path.suffix.lower() in SUPPORTED_SUFFIXES
        or relative_path.name.lower() in SUPPORTED_FILENAMES
    )


def is_excluded(relative_path: PurePosixPath) -> bool:
    """Apply the same exclusions used by the CocoIndex source walker."""
    path = relative_path.as_posix()
    return any(fnmatchcase(path, pattern) for pattern in EXCLUDED_PATTERNS)


def iter_source_files() -> Iterator[tuple[PurePosixPath, Path]]:
    """Yield all currently selected source files in deterministic order."""
    selected: list[tuple[PurePosixPath, Path]] = []
    for source_root in SOURCE_ROOTS:
        absolute_root = PROJECT_ROOT.joinpath(*source_root.parts)
        for absolute_path in absolute_root.rglob("*"):
            if not absolute_path.is_file():
                continue
            relative_path = PurePosixPath(
                absolute_path.relative_to(PROJECT_ROOT).as_posix()
            )
            if is_supported(relative_path) and not is_excluded(relative_path):
                selected.append((relative_path, absolute_path))
    yield from sorted(selected, key=lambda item: item[0].as_posix())


def language_for_path(relative_path: PurePosixPath) -> str | None:
    """Return the parser language override for a source path."""
    return LANGUAGE_BY_SUFFIX.get(relative_path.suffix.lower())


def source_kind_for_path(relative_path: PurePosixPath) -> str:
    """Classify source authority without excluding tests from retrieval."""
    path = relative_path.as_posix().lower()
    name = relative_path.name.lower()
    if "/src/test/" in path or "/e2e/" in path or ".test." in name or ".spec." in name:
        return "test"
    if "/zosassets/" in path or "/operations/" in path:
        return "generated_contract"
    if "/legacy-static/" in path:
        return "legacy_frontend"
    return "production"


def feature_for_path(relative_path: PurePosixPath) -> str | None:
    """Derive a stable coarse feature label from established source folders."""
    parts = relative_path.parts
    if "features" in parts:
        index = parts.index("features")
        if index + 1 < len(parts):
            return parts[index + 1]

    marker = "mainframemodernization"
    if marker in parts:
        index = parts.index(marker)
        if index + 1 < len(parts):
            return parts[index + 1]

    if "zosAssets" in parts:
        index = parts.index("zosAssets")
        if index + 1 < len(parts):
            return parts[index + 1].lower()

    return None
