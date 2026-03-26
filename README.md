# Graph-RAG API

Lightweight graph + vector dual retrieval pipeline with FastAPI.
Plug in **any OpenAI-compatible LLM provider** — no code changes needed.

## Quick start

```bash
# 1. install deps
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # optional, for better NER

# 2. configure
cp .env.example .env
# edit .env with your keys and preferred provider

# 3. run
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Provider configuration

Edit `.env` — no code changes:

| Provider       | LLM_BASE_URL                                              | LLM_MODEL example        |
|----------------|-----------------------------------------------------------|--------------------------|
| OpenRouter     | https://openrouter.ai/api/v1                              | qwen/qwen3-8b            |
| Qwen API       | https://dashscope.aliyuncs.com/compatible-mode/v1        | qwen-plus                |
| OpenAI         | https://api.openai.com/v1                                 | gpt-4o-mini              |
| Together AI    | https://api.together.xyz/v1                               | meta-llama/Llama-3-8b    |
| Groq           | https://api.groq.com/openai/v1                            | llama-3.1-8b-instant     |
| Mistral        | https://api.mistral.ai/v1                                 | mistral-small-latest     |
| Ollama (local) | http://localhost:11434/v1                                 | qwen2.5:7b               |
| LM Studio      | http://localhost:1234/v1                                  | any loaded model         |

> **Embeddings** can use a different provider than the LLM.
> Set `EMBED_BASE_URL` and `EMBED_API_KEY` separately.
> For local embeddings via Ollama: `EMBED_BASE_URL=http://localhost:11434/v1`, `EMBED_MODEL=nomic-embed-text`.

## API endpoints

| Method | Path      | Description                        |
|--------|-----------|------------------------------------|
| GET    | /health   | Status, model info, chunk count    |
| POST   | /ingest   | Add a document to the knowledge base |
| POST   | /query    | Ask a question (dual retrieval + LLM) |
| GET    | /graph    | Inspect entity graph (nodes + edges) |

## Example usage

```bash
# ingest
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Elon Musk founded SpaceX in 2002. SpaceX is based in Hawthorne, California.", "metadata": {"source": "test"}}'

# query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who founded SpaceX and where is it located?"}'
```

## Architecture

```
POST /ingest  →  chunk text  →  embed (batch)  →  ChromaDB
                              →  extract entities (spaCy)  →  NetworkX graph

POST /query   →  embed question  →  vector search (ChromaDB)
                               →  entity NER  →  graph BFS expand
                               →  merge + rerank  →  LLM (any provider)
```

## Swap components

- **Graph DB**: replace `NetworkX` in `app/graph_store.py` with Neo4j — same interface
- **Vector DB**: replace `ChromaDB` in `app/vector_store.py` with Qdrant/FAISS
- **NER**: replace spaCy in `app/entities.py` with an LLM-based extractor
- **Chunker**: replace word-splitter in `app/ingest.py` with `tiktoken`-based splitter
# lexbot
# lexbot
# lexbot
# lexbot
