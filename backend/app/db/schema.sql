-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    num_chunks INTEGER DEFAULT 0,
    status TEXT DEFAULT 'processing' -- processing | ready | failed
);

-- Chunks table with detailed source grounding metadata
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    page_number INTEGER,          -- PDF pages, or CSV/TXT row markers
    line_or_row_range TEXT,       -- e.g. "40-55" for txt, "rows 12-20" for csv
    char_start INTEGER,
    char_end INTEGER,
    embedding BLOB NOT NULL       -- raw float vector bytes
);

-- Chat history table
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,           -- user | assistant
    content TEXT NOT NULL,
    citations_json TEXT,          -- validated citations JSON array
    grounded BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id);
