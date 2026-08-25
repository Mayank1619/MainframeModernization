# Codebase RAG pipeline

This pipeline indexes selected text files from `frontend/` and `backend/api/`.
CocoIndex incrementally maintains one canonical manifest per source file, Tree-sitter
connects syntax nodes to size-bounded chunks, Groq creates concise summaries, and
LanceDB stores the local CodeRankEmbed vectors.

## Setup

```bash
cd /Users/temp/Documents/pod/MainframeModernization
python3 -m venv rag/.venv
rag/.venv/bin/pip install -r rag/requirements.txt
```

Create `rag/.env` with the existing local Groq key:

```dotenv
GROQ_API_KEY=your_key_here
```

The summarization model defaults to `openai/gpt-oss-120b`. The embedding model is
the pinned `nomic-ai/CodeRankEmbed` revision already used by `embedding_model.py`.

## Incremental refresh

There is intentionally no orchestrator yet. Run these steps from the project root:

```bash
rag/.venv/bin/cocoindex update rag/ingestion.py
rag/.venv/bin/python -m rag.validate_manifests
rag/.venv/bin/python -m rag.analyze_manifests
rag/.venv/bin/python -m rag.ai_summary_input
rag/.venv/bin/python -m rag.generate_ai_summaries
rag/.venv/bin/python -m rag.create_embedding_text
rag/.venv/bin/python -m rag.sync_embedding_table
rag/.venv/bin/python -m rag.embedding_model --device mps
```

`analyze_manifests` records added, modified, and removed paths in
`rag/output/.analysis_history.json`. The three summary-input JSON files and three
summary CSV files represent only that latest change set. A stale analysis or mixed
summary run is rejected before embedding inputs can be changed.

`rag/input_embeddings/` is different: it remains the complete current snapshot.
`create_embedding_text` replaces only changed/new per-file JSONs and removes only
deleted or newly empty files. This allows `sync_embedding_table` to preserve vectors
whose `embedding_text` is unchanged, mark new/changed rows as pending, and delete
only obsolete chunks. `embedding_model` then embeds pending rows only.

If the summary/vector outputs must be rebuilt from every current manifest, export
all nonempty files once with:

```bash
rag/.venv/bin/python -m rag.ai_summary_input --all
```

Then continue with `generate_ai_summaries`, `create_embedding_text`, table sync, and
embedding. The `--all` path calls Groq for the full corpus, so it is not used during
normal repository updates.

## Chunk structure

Manifests mirror source paths under `rag/output/manifests/` and contain readable
path-based file, node, and chunk IDs. Chunking uses a 2400-byte target, a 500-byte
minimum, and zero overlap. Tree-sitter-backed boundaries connect classes/functions
to chunks through `parent_node_id` and `related_node_ids`.

Summary handling follows three cases:

- A single-chunk file receives its file summary in that chunk's `embedding_text`.
- A multi-chunk file receives the same file summary in every one of its chunks.
- A callable node spanning multiple chunks also adds its node summary only to the
  chunks linked to that node.

Canonical manifests remain unchanged and preserve null summary fields. Enrichment
lives only in the flat per-file JSONs under `rag/input_embeddings/`.
