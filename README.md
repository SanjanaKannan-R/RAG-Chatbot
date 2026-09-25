# Citation-Grounded RAG Chatbot (Flask + LangChain + SQLite-Vec + React)

A full-stack Retrieval-Augmented Generation (RAG) chatbot that allows users to chat with their PDFs, `.txt`, and `.csv` files with a **non-negotiable factual grounding guarantee**: **every claim in every answer must cite the exact source chunk it came from** — file name, chunk index, page/row number, and literal chunk text — verifiable by the user.

If an answer cannot be grounded in retrieved document chunks, the system flags `grounded: false` with a visible warning rather than hallucinating.

---

## 🏛️ Architecture & Verification Pipeline

```
  ┌─────────────────┐       ┌────────────────────┐       ┌────────────────────────┐
  │  Document Upload│ ───>  │ Chunker & Offsets  │ ───>  │  SQLite Database       │
  │ (PDF / TXT / CSV│       │ Page/Row Tracking  │       │ (Metadata + sqlite-vec)│
  └─────────────────┘       └────────────────────┘       └───────────┬────────────┘
                                                                     │
  ┌──────────────────────────────────────────────────────────────────┘
  ▼
┌─────────────────────────┐       ┌────────────────────────┐       ┌────────────────────────┐
│ Vector Search (Top-K)   │ ───>  │ Prompt with Labeled    │ ───>  │ LLM Generation         │
│ Cosine Similarity Match │       │ [chunk_id: X | file: Y]│       │ (JSON Structured Mode) │
└─────────────────────────┘       └────────────────────────┘       └───────────┬────────────┘
                                                                               │
  ┌────────────────────────────────────────────────────────────────────────────┘
  ▼
┌──────────────────────────────────────────────────────────┐
│ SERVER-SIDE CITATION VALIDATOR (Authoritative Check)     │
│ 1. Must be in retrieved set for this query (strip fakes) │
│ 2. Query true metadata & literal text from SQLite        │
│ 3. Match quoted snippet & calculate exact char offsets   │
│ 4. If empty or ungrounded -> flag grounded: false        │
└─────────────────────────────┬────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────┐
│ REACT FRONTEND (Tailwind CSS + Lucide Icons)             │
│ • Clickable citation chips: [invoice.pdf, p.1]           │
│ • Inline expandable cards with literal stored chunk text │
│ • Quoted claims highlighted directly inside chunk        │
│ • Distinct warning bubble when answer is ungrounded      │
└──────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack

- **Backend:** Python 3.11+, **Flask**, Werkzeug, LangChain (`RecursiveCharacterTextSplitter`), `sqlite-vec`
- **Database:** Single SQLite file (`rag.db`) storing:
  - `documents`: document metadata, status, chunk counts
  - `chunks`: chunk texts, page numbers, line/row ranges, char offsets, vector BLOBs
  - `vec_chunks`: `sqlite-vec` `vec0` virtual table for ANN cosine similarity search
  - `chat_history`: conversation sessions, queries, answers, verified citations JSON
- **Embeddings:** Pluggable:
  - `local` (deterministic fast tokenizer & subword hashing — instant out-of-the-box local execution)
  - `sentence-transformers` (local, free HuggingFace models like `all-MiniLM-L6-v2`)
  - `openai` (`text-embedding-3-small`)
- **LLM for Generation:** Pluggable:
  - `openai` / `groq` (ultra-fast JSON mode with `openai/gpt-oss-120b`, `gpt-4o-mini`, etc.)
  - `anthropic` (`claude-3-5-sonnet`)
  - `ollama` (`llama3`, `mistral`, local models)
  - `rule` (offline grounded extractive engine for testing)
- **Frontend:** React + Vite + Tailwind CSS v4 + TypeScript + Lucide Icons

---

## 📂 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                      # Flask app & REST endpoints
│   │   ├── models.py                    # Pydantic request/response schemas
│   │   ├── db/
│   │   │   ├── schema.sql               # SQLite DDL (documents, chunks, chat_history)
│   │   │   └── session.py               # Connection pool & sqlite-vec extension loader
│   │   ├── ingestion/
│   │   │   ├── chunker.py               # File type router
│   │   │   ├── pdf_loader.py            # PDF page extraction & chunking (pypdf/pdfplumber)
│   │   │   ├── txt_loader.py            # TXT paragraph & line range chunking
│   │   │   ├── csv_loader.py            # CSV row-group chunking with headers
│   │   │   └── ingest_service.py        # Complete ingestion & indexing service
│   │   ├── retrieval/
│   │   │   ├── embeddings.py            # Pluggable embedding providers
│   │   │   └── vector_search.py         # sqlite-vec cosine similarity search
│   │   └── generation/
│   │       ├── llm_provider.py          # Pluggable LLM provider (Groq/OpenAI/Anthropic/Ollama)
│   │       ├── prompt_templates.py      # Labeled context prompts ([chunk_id: X])
│   │       └── citation_validator.py    # Strict server-side verification against SQLite
│   ├── tests/                           # Step-by-step test suites (Steps 1, 2, 3, 6, 7, 8, 10)
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                             # Configured with Groq credentials
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx           # Chat stream, ungrounded alert, input bar
│   │   │   ├── CitationChip.tsx         # Clickable chips with expandable source verification
│   │   │   ├── DocumentSidebar.tsx      # Document manager, status badges, delete buttons
│   │   │   └── UploadBox.tsx            # Drag-and-drop uploader for PDF, TXT, CSV
│   │   ├── App.tsx                      # Main single-page application state
│   │   ├── types.ts                     # TypeScript data interfaces
│   │   └── index.css                    # Tailwind CSS v4 theme
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## 🚀 Running the Application

### 1. Run the Flask Backend
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python backend/app/main.py
```
Backend runs at: `http://127.0.0.1:8000`

### 2. Run the React Frontend
```powershell
cd frontend
npm run dev
```
Frontend runs at: `http://127.0.0.1:5173`
#   R A G - C h a t b o t  
 #   R A G - C h a t b o t  
 #   R A G - C h a t b o t  
 