# Financial Report RAG

Five-minute speaker notes

## 1. Financial Report RAG

0:00–0:35 (35 seconds)
My project answers questions about the American Express 2025 annual report using retrieval augmented generation, or RAG. The idea is to find relevant passages first, then give those passages to a language model as evidence. Financial reports make this challenging because answers can sit inside tables, footnotes, or several different sections. My goal is to return a useful answer with a traceable source, and to identify where the retrieval step still needs improvement. I'll cover the pipeline, one saved example, and the evaluation results.

## 2. The pipeline

0:35–1:30 (55 seconds)
The pipeline has an offline preparation stage and a question answering stage. First, the ingestion code extracts the annual report and creates report-aware chunks. The current corpus contains 523 chunks. Each record includes source metadata such as page, section, and content type, so retrieval results can later become citations. Next, all-MiniLM-L6-v2 converts chunk text into normalized embeddings, which the project stores alongside aligned metadata. At question time, hybrid search ranks the chunks and normally retrieves the top five. The application restores their source metadata, sends the evidence to the generation module, and saves the answer and retrieval scores for inspection. This gives me visibility into both what the model answered and which evidence it actually received.

## 3. Hybrid retrieval

1:30–2:20 (50 seconds)
The retriever combines semantic similarity with lexical matching. Semantic similarity helps when a question uses different wording from the report. BM25-style matching helps preserve exact financial terms and labels. The current ranking formula gives normalized semantic scores a weight of 0.4 and normalized lexical scores a weight of 0.6, then adds an exact-phrase boost. Those are implementation settings, not a claim that the weights are optimal. The retriever returns separate semantic, lexical, and hybrid scores, which makes failures easier to diagnose. For example, a passage can match the words CEO and shareholders while still failing to contain the CEO's message. That is why ranking quality matters even when an answer model can write fluently.

## 4. A saved answer with a traceable source

2:20–3:10 (50 seconds)
Here is an actual saved run, rather than a hypothetical demo. The user asked what the major revenue generator was in 2025. The generated answer identified discount revenue at 37.4 billion dollars and cited chunk 127 on page 63. That supporting chunk appeared fourth in the retrieved results, so retaining several candidates mattered in this example. The generation prompt asks the model to answer only from the supplied evidence and to say when the context is insufficient. The code also checks whether cited chunk IDs belong to the retrieved evidence. That check helps catch invented IDs, but it does not establish that every claim is supported or that a page label is correct. Claim-level verification remains a useful next step.

## 5. Retrieval results and failure cases

3:10–4:15 (65 seconds)
The saved development evaluation contains twenty questions, with five in each of four categories. Recall at five is 80 percent for factual questions and keyword questions, 40 percent for ambiguous questions, and 30 percent for questions requiring multiple chunks. Recall measures how much of the labeled relevant evidence appears in the first five results. It is not answer accuracy. These are small category samples, so I treat the numbers as diagnostic evidence rather than a broad performance guarantee. A separate saved run on twenty-four ambiguous questions reports recall at five of about 35.4 percent. The application logs also show the failure mode directly: questions about the CEO's message retrieve board and executive listings, and the answer model abstains. Together, these results point toward query interpretation and evidence coverage as the main areas to improve.

## 6. Next steps

4:15–5:00 (45 seconds)
The project now connects document ingestion, hybrid retrieval, and cited generation in an inspectable workflow. My next priority is improving the evidence that reaches the model. I would compare semantic-only, lexical-only, and hybrid baselines on the same labeled set, then test reranking and query reformulation on ambiguous questions. I would also audit section metadata, because some saved results carry broad or misleading section labels, and test ways to collect evidence across multiple chunks. Finally, I would evaluate whether each answer claim is supported, alongside retrieval metrics and abstention behavior. The main lesson from this project is that grounded generation depends on retrieving the right evidence, and the saved diagnostics make those weaknesses visible.