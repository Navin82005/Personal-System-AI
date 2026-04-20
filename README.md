# Personal System AI (RAG Based)

## Overview
The Personal System AI (First Version) has been implemented focusing entirely on Document Intelligence. It provides a modular, maintainable, and highly scalable RAG-based backend using Python, FastAPI, and ChromaDB.

The system is able to:
1. Systematically detect and load content from PDF, DOCX, TXT, Markdown, Python, JSON, YAML, Java, and other text-based files.
2. Break documents into semantic chunks.
3. Automatically embed and securely store these chunks in a local vector database.
4. Process natural language questions to retrieve contextual snippets.
5. Provide grounded answers using an LLM (configured for Groq with `llama-3.1-8b-instant`).
6. Support **File-Specific Queries**: Restrict queries to a specific file simply by mentioning the filename in the prompt (e.g., "What does architecture_notes.md say?").

## Architecture Highlights
The project is strictly separated into modular components:
- `ingestion/`: Handles `folder_scanner.py`, `document_loader.py` (which powers multi-format loading), `chunking.py`, and the orchestrator `embedding_pipeline.py`.
- `vector_store/`: Handles `vector_db.py`, safely wrapping ChromaDB and local SentenceTransformers embeddings.
- `rag/`: Implements the `retriever.py`, `prompt_builder.py`, and `generator.py` for pipeline robustness.
- `api/chat_routes.py`: Re-usable FastAPI routes connecting the components.

## Setup & Running the API
The project requires Python 3.11.

1. **Install Dependencies:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Configure Environment Variables:**
Create a `.env` file in the root directory and add your Groq API Key:
```text
GROQ_API_KEY="gsk_your_api_key_here"
```

For **LiveKit voice**, also set:
```text
LIVEKIT_URL="wss://your-livekit-server"
LIVEKIT_API_KEY="..."
LIVEKIT_API_SECRET="..."
```

3. **Start the FastAPI Server:**
```bash
uvicorn main:app --reload
```

## How to Test

You can run the included integration test script which simulates end-to-end usage:
```bash
python test_pipeline.py
```

### Usage Examples (via API or Swagger)

Once the server is running on `http://127.0.0.1:8000`, you can interact with the Swagger docs at `http://127.0.0.1:8000/docs`, or use tools like `curl`.

**1. Scan a folder and index documents:**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/scan-folder' \
  -H 'Content-Type: application/json' \
  -d '{
  "folder_path": "/Users/naveenn/Documents/Projects/Personal System AI/test_data"
}'
```
This returns a `job_id`. Track progress via:
```bash
curl -X 'GET' "http://127.0.0.1:8000/progress/<job_id>"
```

## Voice (LiveKit)

Frontend needs `VITE_LIVEKIT_URL` set (Vite env), for example in `frontend/.env`:
```text
VITE_LIVEKIT_URL="wss://your-livekit-server"
```

The Chat view includes a mic toggle that:
- starts the backend voice agent for the room
- joins the LiveKit room
- streams user audio -> STT -> RAG -> TTS -> streamed assistant audio

**2. List Indexed Documents:**
```bash
curl -X 'GET' 'http://127.0.0.1:8000/documents'
```

**3. Query the Assistant (Global Search):**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/query' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "What is the Personal System AI?",
  "top_k": 3
}'
```
*Note: Make sure your `GROQ_API_KEY` is set in either the environment or a `.env` file for the query stage to successfully generate text.*

**4. Query the Assistant (File-Specific Search):**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/query' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "What does it say in architecture_notes.md?",
  "top_k": 3
}'
```
*The system will automatically detect the file name `architecture_notes.md`, verify if it is indexed, and restrict the vector search strictly to that document. If the document doesn't exist, it will immediately return an error message without calling the LLM.*
