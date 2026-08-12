# FloatChat

A chatbot for ArgoData, providing insights and summary on given Argo data around India.

## How it works

```
Frontend (React + Vite, :5173)
        │  POST /chat
        ▼
client_service.py (FastAPI, :8001)
        │  mcp-use agent (gpt-4o-mini)
        ▼
S/ocean.py (MCP server, tool: summarize_ocean_data)
        ├── Chroma  ./chroma        → resolves a place name to lat/lon
        └── Postgres  argofinal     → fetches Argo parameter readings
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (`pip install uv`) — it installs Python 3.13 for you
- Node.js 18+

## Setup

1. Fill in `.env` in the project root (see `.env.example`):

   ```
   YOUR_OPENAI_API_KEY=sk-...
   POSTGRES_URI=postgresql+psycopg2://user:password@host/dbname?sslmode=require
   ```

2. Install dependencies:

   ```powershell
   uv sync
   cd Frontend; npm install
   ```

## Running

Two terminals, both from the project root.

**Backend** — must run from the project root so the MCP server in `S/ocean.py` is found:

```powershell
uv run uvicorn client_service:app --host 127.0.0.1 --port 8001
```

**Frontend:**

```powershell
cd Frontend
npm run dev
```

Then open http://localhost:5173.

The frontend posts to `http://127.0.0.1:8001/chat`, so the backend must be on port 8001
(or change the URL in [MessageBox.jsx](Frontend/src/components/MessageBox.jsx)).

Check the backend is alive: `curl http://127.0.0.1:8001/health`

## Data / ingestion scripts

These are one-off utilities, not part of the running app:

- [main.py](main.py) — scrapes island coordinates from OpenStreetMap into `data/indian_islands.csv`
- [S/newembed.py](S/newembed.py) — embeds the `data/*.csv` landmarks into the `water_landmarks` Chroma collection
- [embeddings.py](embeddings.py) — embeds Argo rows from Postgres into an `argo_embeddings` Chroma collection
- [S/query_chroma.py](S/query_chroma.py), [test.py](test.py) — query helpers for inspecting Chroma
- [S/client.py](S/client.py) — terminal chat client (same agent as the API, without FastAPI)

The `chroma/` directory is checked in and already contains 3,916 `water_landmarks`
embeddings, so you do not need to re-run the ingestion to use the chat.
