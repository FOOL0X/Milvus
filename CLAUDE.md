# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG智能客服助手 — A RAG (Retrieval-Augmented Generation) customer service system using Milvus vector database, LangChain, and LLM (GPT-4o/Claude 3.5/MiniMax).

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   Milvus    │
│   (React)   │◀────│  (FastAPI)  │◀────│  (VectorDB) │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │  LLM API    │
                    │ (MiniMax)   │
                    └─────────────┘
```

- **Frontend**: React 18 + Vite + Tailwind + Zustand (state management)
- **Backend**: FastAPI with LangChain, routes in `src/api/routers/`
- **Vector Store**: Milvus 2.5 with etcd (HNSW index, COSINE metric)
- **Embeddings**: BGE-M3 model (FlagEmbedding) — generates both dense + sparse vectors
- **LLM**: Configurable (default MiniMax via OpenAI-compatible API)

## Commands

### Backend Development
```bash
cd backend

# Install dependencies (uses uv)
uv sync

# Run development server with hot reload
uv run uvicorn src.api.main:app --reload

# Run tests
uv run pytest

# Run a single test file
uv run pytest tests/test_file.py -v
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Data Ingestion
```bash
cd backend

# Import directory of documents (auto-detects format: pdf, docx, txt, xml, json, md, sqlite)
python scripts/ingest_data.py --path ./data/docs --collection customer_service_kb

# Import Gatling plugins XML (dense + sparse vectors)
python scripts/ingest_data.py --path ./plugins.xml --collection plugins

# Import with custom chunking
python scripts/ingest_data.py --path ./data/docs --collection kb --chunk-size 512 --chunk-overlap 100
```

### Docker Compose (Full Stack)
```bash
docker-compose up -d
# Access at http://localhost
```

## Key Backend Modules

| Module | Purpose |
|--------|---------|
| `src/core/config.py` | Settings via Pydantic (Milvus URI, LLM API keys, model names) |
| `src/core/embeddings.py` | `BGEM3Embeddings` — loads BGE-M3 model, generates dense+sparse vectors |
| `src/core/vector_store.py` | `VectorStoreService` — Milvus connection, collection schema (HNSW index) |
| `src/services/search.py` | `SearchService` (similarity search) + `ChatService` (ConversationalRetrievalChain) |
| `src/services/ingest.py` | `IngestService` — document loading (PDF/DOCX/TXT), chunking, Milvus ingestion |
| `src/api/routers/chat.py` | `/api/chat` endpoint with in-memory session storage |
| `src/api/routers/ingest.py` | `/api/ingest` endpoint for file uploads |

## Vector Store Schema

Milvus collection `customer_service_kb` uses HNSW index with COSINE similarity. Schema includes fields: `id`, `chunk_text`, `plugin_id`, `plugin_name`, `description`, `category`, `cvss3`, etc.

The `plugins` collection uses a different schema with separate `dense_vector` (1024-dim) and `sparse_vector` fields for hybrid search.

## Environment Variables

Key variables in `.env`:
- `MILVUS_URI` — Milvus server URI (default: `http://milvus:19530`)
- `OPENAI_API_KEY` / `OPENAI_API_BASE` — LLM API credentials
- `OPENAI_MODEL` — LLM model name (default: `MiniMax-M2.7`)
- `EMBEDDING_MODEL` — Path to BGE-M3 model (default: `models/bge-m3`)
- `DEFAULT_COLLECTION` — Default Milvus collection name

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message, returns answer + sources |
| `/api/chat/history/{session_id}` | GET | Get session chat history |
| `/api/ingest` | POST | Upload document (multipart) |
| `/api/health` | GET | Health check with Milvus connection status |

## Data Ingestion Formats

The `ingest_data.py` script auto-detects format by extension:
- `.pdf` / `.docx` / `.txt` — document loaders
- `.xml` — if contains `<RECORD>` with `pluginid` → plugins format; otherwise FAQ format
- `.json` — structured JSON
- `.md` — Markdown (split by headings/paragraphs)
- `.db` / `.sqlite` / `.sqlite3` — SQLite database tables
