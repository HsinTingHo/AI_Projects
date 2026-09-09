# RAG Document Search

This project cleans source documents, splits them into retrieval chunks, embeds
those chunks with `all-MiniLM-L6-v2`, and runs semantic search or retrieval
evaluation.

Run every command from the project root:

```bash
cd /Users/eva/Desktop/Projects/AI_Project
```

## Setup

The project uses the Python 3.12 virtual environment named `.semanticSearch312`.
Install the core dependencies with:

```bash
./.semanticSearch312/bin/pip install -r requirements.txt
```

The annual-report PDF chunker additionally needs its PDF-extraction helpers:

```bash
./.semanticSearch312/bin/pip install PyMuPDF pdfplumber requests tiktoken
```

The first embedding or search run may download `all-MiniLM-L6-v2` from Hugging
Face. Internet access is required unless the model is already cached locally.

## Files and outputs

| Location | Purpose |
| --- | --- |
| `resources/corpus/originals/financialStatement/` | Source annual-report PDF files. |
| `resources/corpus/cleaned/financialStatement/` | Cleaned text files used by the basic chunker. |
| `resources/corpus/american_express_2025_chunks.jsonl` | Annual-report chunks with section and page metadata. |
| `resources/corpus/embedded/` | Saved NumPy embeddings and their matching metadata. |

## Run each script manually

### 1. Clean HTML or PDF source files

`load_documents.py` reads supported `.html`, `.htm`, and `.pdf` files from
`resources/corpus/originals/financialStatement/` and writes cleaned `.txt`
files to `resources/corpus/cleaned/`.

```bash
./.semanticSearch312/bin/python src/ingestion/load_documents.py
```

The script leaves an existing cleaned file unchanged. To re-clean a document,
remove or rename that individual cleaned output first.

### 2. Chunk cleaned text files

`chunk_documents.py` reads `.txt` files from
`resources/corpus/cleaned/financialStatement/`, produces roughly 350-word
chunks with 60-word overlap, and writes JSON Lines to
`resources/corpus/chunks`.

```bash
./.semanticSearch312/bin/python src/ingestion/chunk_documents.py
```

> The basic cleaner writes to `resources/corpus/cleaned/`, while this chunker
> currently reads the `financialStatement` subfolder. Place the cleaned annual
> report in `resources/corpus/cleaned/financialStatement/` before using this
> command.

### 3. Create annual-report-aware chunks

`load_financial_statements.py` is the richer annual-report pipeline. It
preserves document, year, section, subsection, page, content type, and table
metadata in the JSONL output.

Use the local PDF already in the repository:

```bash
./.semanticSearch312/bin/python src/ingestion/load_financial_statements.py \
  --no-download \
  --pdf resources/corpus/originals/financialStatement/American-Express-Annual-Report-2025.pdf \
  --output resources/corpus/american_express_2025_chunks.jsonl
```

To download instead, omit `--no-download` and supply a working PDF URL:

```bash
./.semanticSearch312/bin/python src/ingestion/load_financial_statements.py \
  --url "https://example.com/annual-report.pdf" \
  --pdf resources/corpus/originals/financialStatement/report.pdf \
  --output resources/corpus/report_chunks.jsonl
```

### 4. Embed chunks

`embed_documents.py` reads the annual-report JSONL file by default and saves
`context_aware_embeddings.npy` plus
`context_aware_embeddings_metadata.json` in `resources/corpus/embedded/`.

```bash
./.semanticSearch312/bin/python src/ingestion/embed_documents.py
```

Pass custom paths or settings when needed:

```bash
./.semanticSearch312/bin/python src/ingestion/embed_documents.py \
  --chunks-path resources/corpus/american_express_2025_chunks.jsonl \
  --output-dir resources/corpus/embedded \
  --output-filename context_aware_embeddings \
  --batch-size 32 \
  --model-name all-MiniLM-L6-v2
```

Use `--help` to see all available options:

```bash
./.semanticSearch312/bin/python src/ingestion/embed_documents.py --help
```

### 5. Run semantic search

`semanticSearch.py` loads
`resources/corpus/embedded/context_aware_embeddings.npy` and runs the sample
queries declared in its `queries` list.

```bash
./.semanticSearch312/bin/python src/retrival/semanticSearch.py
```

To search for a different question, edit the `queries` list near the bottom of
`src/retrival/semanticSearch.py`, then run the same command again.

### 6. Evaluate retrieval quality

`evaluate_search.py` reads `resources/corpus/labled_queries.txt` and prints
average Recall@5, nDCG@5, and MRR for each query category.

```bash
./.semanticSearch312/bin/python src/evaluation/evaluate_search.py
```

This evaluation uses `resources/corpus/embedded/embeddings.npy` and
`metadata.json`. These are a legacy artifact pair that is already present in
the repository. The current annual-report embedding command instead creates
`context_aware_embeddings.npy` and
`context_aware_embeddings_metadata.json`; update the evaluator's constants if
you want it to evaluate that annual-report output.

## Typical annual-report workflow

```bash
./.semanticSearch312/bin/python src/ingestion/load_financial_statements.py \
  --no-download \
  --pdf resources/corpus/originals/financialStatement/American-Express-Annual-Report-2025.pdf \
  --output resources/corpus/american_express_2025_chunks.jsonl

./.semanticSearch312/bin/python src/ingestion/embed_documents.py

./.semanticSearch312/bin/python src/retrival/semanticSearch.py
```
