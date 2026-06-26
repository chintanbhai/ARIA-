# AI Research Assistant

A full-stack GenAI project covering **Agentic AI**, **Vector DB**, **Memory**, and **Tool Use**.

## Architecture

```
User → Orchestrator Agent → [Researcher, Summariser, Retriever, Writer]
                                      ↓                    ↓
                              Memory System          Vector DB (Qdrant)
                                      ↓
                              Tool Layer (Web Search, PDF, Python REPL)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Anthropic Claude (claude-sonnet-4-20250514) |
| Agent Framework | LangGraph |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector DB | Qdrant (in-memory for dev, persistent for prod) |
| Short-term Memory | In-process conversation history |
| Long-term Memory | JSON file store + vector search |
| Web Search | Tavily API |
| Backend | FastAPI + Python 3.11+ |
| Frontend | Vanilla HTML/CSS/JS (no build step) |

## Setup

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required keys:
- `ANTHROPIC_API_KEY` — get from https://console.anthropic.com
- `TAVILY_API_KEY` — get from https://tavily.com (free tier available)

### 3. Run the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Open the frontend

Open `frontend/index.html` in your browser, or serve it:

```bash
cd frontend
python -m http.server 3000
```

Then visit http://localhost:3000

## Features

- **Multi-agent orchestration** — Orchestrator plans and delegates to specialized agents
- **Web research** — Researcher agent searches and scrapes the web
- **RAG pipeline** — Documents chunked, embedded, stored in Qdrant, retrieved semantically
- **Dual memory** — Short-term (conversation) + Long-term (persistent facts)
- **Tool use** — Web search, Wikipedia, Python execution
- **Cited answers** — Writer agent produces answers with source citations
- **Research history** — All past research sessions stored and searchable

## Project Structure

```
ai-research-assistant/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   ├── agents/
│   │   ├── orchestrator.py  # Main LangGraph agent graph
│   │   ├── researcher.py    # Web search + scraping agent
│   │   ├── summariser.py    # Chunking + embedding agent
│   │   ├── retriever.py     # Semantic search agent
│   │   └── writer.py        # Answer synthesis agent
│   ├── memory/
│   │   ├── short_term.py    # Conversation context manager
│   │   └── long_term.py     # Persistent memory store
│   ├── tools/
│   │   ├── web_search.py    # Tavily web search tool
│   │   ├── wikipedia.py     # Wikipedia lookup tool
│   │   └── python_repl.py   # Safe Python execution tool
│   └── routers/
│       ├── chat.py          # Chat endpoint
│       ├── research.py      # Research trigger endpoint
│       └── memory.py        # Memory management endpoints
└── frontend/
    ├── index.html           # Main UI
    ├── src/
    │   ├── app.js           # Main application logic
    │   ├── api.js           # Backend API calls
    │   └── components/      # UI components
    └── styles/
        └── main.css
```
