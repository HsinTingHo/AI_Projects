# Financial Report RAG Search

This project builds and evaluates hybrid retrieval over the American Express
2025 annual report. It extracts report-aware chunks, embeds them with
`all-MiniLM-L6-v2`, and ranks chunks with semantic similarity, BM25-style
lexical matching, and exact-phrase boosts.

Run commands from the project root:

```bash
cd /Users/eva/Desktop/Projects/AI_Project
```

## Setup

The project uses the Python 3.12 environment at `.semanticSearch312`.

```bash
./.semanticSearch312/bin/pip install -r requirements.txt
```

The annual-report PDF chunker also requires PDF-extraction helpers:

```bash
./.semanticSearch312/bin/pip install PyMuPDF pdfplumber requests tiktoken
```

The first embedding or search run may download `all-MiniLM-L6-v2` from
Hugging Face. Later runs use the local model cache when available.

## Project data flow

```text
Annual-report PDF
  → annual-report-aware JSONL chunks
  → embeddings + metadata
  → hybrid semantic search
  → cited, grounded LLM answer
  → evaluation metrics + ranking diagnostics
```

| Artifact | Purpose |
| --- | --- |
| `resources/corpus/originals/financialStatement/` | Source PDF files. |
| `resources/corpus/american_express_2025_chunks.jsonl` | Annual-report chunks with page, section, subsection, and table metadata. |
| `resources/corpus/embedded/context_aware_embeddings.npy` | Normalized chunk vectors. |
| `resources/corpus/embedded/context_aware_embeddings_metadata.json` | Chunk text and metadata aligned to the vector indexes. |
| `resources/evaluations/*.jsonl` | Evaluation queries and expected answer chunk IDs. |
| `resources/evaluations/results/<version>/` | Saved metrics and ranking-debug output. |

## Recommended annual-report workflow

### 1. Create report-aware chunks

`load_financial_statements.py` is the recommended annual-report ingestion
tool. It detects narrative sections, risks, tables, and footnotes, then writes
JSONL records with report metadata.

```bash
./.semanticSearch312/bin/python src/ingestion/load_financial_statements.py \
  --no-download \
  --pdf resources/corpus/originals/financialStatement/American-Express-Annual-Report-2025.pdf \
  --output resources/corpus/american_express_2025_chunks.jsonl
```

To download a different PDF, omit `--no-download` and supply a valid `--url`,
along with the desired local `--pdf` and JSONL `--output` paths.

### 2. Generate embeddings

`embed_documents.py` reads
`resources/corpus/american_express_2025_chunks.jsonl` by default and writes
the matching vector and metadata files to `resources/corpus/embedded/`.

```bash
./.semanticSearch312/bin/python src/ingestion/embed_documents.py
```

Use custom paths, a filename prefix, batch size, or model when needed:

```bash
./.semanticSearch312/bin/python src/ingestion/embed_documents.py \
  --chunks-path resources/corpus/american_express_2025_chunks.jsonl \
  --output-dir resources/corpus/embedded \
  --output-filename context_aware_embeddings \
  --batch-size 32 \
  --model-name all-MiniLM-L6-v2
```

The command creates:

```text
resources/corpus/embedded/context_aware_embeddings.npy
resources/corpus/embedded/context_aware_embeddings_metadata.json
```

### 3. Run hybrid search

`semanticSearch.py` loads the default annual-report embeddings and runs the
sample queries in its `queries` list.

```bash
./.semanticSearch312/bin/python src/retrival/semanticSearch.py
```

To try another question, edit the `queries` list near the bottom of
`src/retrival/semanticSearch.py`, then rerun the command.

Hybrid ranking combines the following signals:

```text
0.4 × normalized semantic similarity
+ 0.6 × normalized BM25 lexical score
+ exact-phrase boost
```

The terminal output includes the chunk ID, hybrid score, semantic score,
lexical score, and a text preview. Chunk IDs are displayed as one-based values
that match the annual-report JSONL `chunk_id` fields.

## Generation

`src/generation/prompt.py` builds a bounded evidence context and requires the
model to cite the retrieved chunks. `src/generation/llm.py` calls the OpenAI
Responses API, returns the answer plus citation-validation details, and reads
its API key only from `FINANCIAL_RAG_API_KEY`.

Install the updated requirements, then set the key in the current terminal:

```bash
./.semanticSearch312/bin/pip install -r requirements.txt
export FINANCIAL_RAG_API_KEY='your-api-key'
```

Use the following example to retrieve five chunks, restore their source
metadata, and generate a grounded answer. Change `model` if your account uses
a different available model.

```bash
./.semanticSearch312/bin/python -c "
import json
from src.retrival.semanticSearch import semantic_search
from src.generation.llm import generate_answer

metadata = json.load(open('resources/corpus/embedded/context_aware_embeddings_metadata.json'))
search_results = semantic_search('What was total revenue in 2025?', top_k=5)
evidence = [metadata[result['index']] for result in search_results]
print(generate_answer('What was total revenue in 2025?', evidence, model='gpt-5'))
"
```

The returned dictionary includes `answer`, `valid_citation_ids`, and
`invalid_citation_ids`. Treat a non-empty `invalid_citation_ids` list as a
grounding failure that should be retried or shown for review.

## Evaluation

`evaluate_search.py` evaluates hybrid retrieval against annual-report JSONL
labels. Each line must contain at least:

```json
{
  "eval_id": "AMEX25-USCS-F02",
  "query": "How much were U.S. Consumer Services' total revenues?",
  "eval_category": "factual_category_1",
  "answer_chunks": [{"chunk_id": 144}]
}
```

`answer_chunks[].chunk_id` is the binary relevance ground truth. The evaluator
reports Recall@5, nDCG@5, and MRR by `eval_category`.

Run the default evaluation file:

```bash
./.semanticSearch312/bin/python src/evaluation/evaluate_search.py
```

Run a specific evaluation file and save versioned artifacts:

```bash
./.semanticSearch312/bin/python src/evaluation/evaluate_search.py \
  --evaluation-file eval_amex_2025_dev_v1.jsonl \
  --version v1
```

When `--version` is present, the evaluator creates:

```text
resources/evaluations/results/v1/
  eval_amex_2025_dev_v1_metrics.v1.jsonl
  eval_amex_2025_dev_v1_rank.v1.jsonl
```

The metrics file contains category averages. The ranking file contains one
record per evaluation query, including expected chunk IDs, first relevant
rank, per-query metrics, and the top 20 ranked chunks with page/section
metadata, hybrid/semantic/lexical scores, relevance flags, and text previews.

Evaluation also prints the top five search results and expected answer chunk
IDs for each query, making it practical to inspect a run in real time.

## Basic HTML/PDF utilities

The following utilities remain available for simple document cleanup and
word-based chunking. The report-aware workflow above is preferred for annual
reports because it preserves table and page metadata.

Clean `.html`, `.htm`, and `.pdf` files from
`resources/corpus/originals/financialStatement/`:

```bash
./.semanticSearch312/bin/python src/ingestion/load_documents.py
```

The cleaner writes `.txt` files to `resources/corpus/cleaned/` and does not
overwrite an existing cleaned file.

Create approximately 350-word chunks with 60-word overlap:

```bash
./.semanticSearch312/bin/python src/ingestion/chunk_documents.py
```

This basic chunker reads from `resources/corpus/cleaned/financialStatement/`
and writes JSONL records to `resources/corpus/chunks`. Place cleaned files in
that subfolder before running it.

## Helpful commands

Show embedding options:

```bash
./.semanticSearch312/bin/python src/ingestion/embed_documents.py --help
```

Show evaluation options:

```bash
./.semanticSearch312/bin/python src/evaluation/evaluate_search.py --help
```
