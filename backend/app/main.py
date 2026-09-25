import os
import json
import uuid
import tempfile
from typing import List, Optional
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

from app.db.session import init_db, get_db_connection
from app.ingestion.ingest_service import IngestionService
from app.retrieval.vector_search import VectorSearchService
from app.retrieval.embeddings import get_embedding_provider
from app.generation.llm_provider import get_llm_provider
from app.generation.citation_validator import CitationValidator
from app.generation.prompt_templates import SYSTEM_PROMPT, build_user_prompt

app = Flask(__name__)

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

try:
    from flask_cors import CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
except Exception:
    pass

# Services initialization
embedding_provider = get_embedding_provider()
init_db(embedding_dim=embedding_provider.dimension)

ingestion_service = IngestionService(embedding_provider=embedding_provider)
vector_search_service = VectorSearchService(embedding_provider=embedding_provider)
llm_provider = get_llm_provider()
citation_validator = CitationValidator()

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


@app.route("/", methods=["GET"])
def read_root():
    return jsonify({
        "status": "healthy",
        "framework": "Flask",
        "app": "Citation-Grounded RAG Chatbot API",
        "embedding_provider": embedding_provider.__class__.__name__,
        "llm_provider": llm_provider.__class__.__name__
    })


@app.route("/documents/upload", methods=["POST"])
def upload_document():
    """
    Accepts PDF, TXT, or CSV, runs ingestion pipeline,
    and returns document ID and ingestion status.
    """
    if "file" not in request.files:
        return jsonify({"detail": "No file uploaded in form data 'file'"}), 400

    file = request.files["file"]
    filename = file.filename or "uploaded_file"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".txt", ".csv", ".md"]:
        return jsonify({
            "detail": f"Unsupported file format '{ext}'. Supported: .pdf, .txt, .csv"
        }), 400

    temp_path = os.path.join(UPLOADS_DIR, f"{uuid.uuid4()}_{filename}")
    try:
        file.save(temp_path)
        result = ingestion_service.ingest_file(temp_path, filename)
        return jsonify({
            "id": result["document_id"],
            "filename": result["filename"],
            "file_type": result["file_type"],
            "uploaded_at": "",
            "num_chunks": result["num_chunks"],
            "status": result["status"]
        }), 200
    except Exception as e:
        return jsonify({"detail": f"Ingestion failed: {str(e)}"}), 500
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.route("/documents", methods=["GET"])
def list_documents():
    """
    List uploaded documents with status and chunk counts.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, filename, file_type, uploaded_at, num_chunks, status
            FROM documents
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        docs = [
            {
                "id": r["id"],
                "filename": r["filename"],
                "file_type": r["file_type"],
                "uploaded_at": str(r["uploaded_at"]),
                "num_chunks": r["num_chunks"] or 0,
                "status": r["status"]
            }
            for r in rows
        ]
        return jsonify(docs), 200
    finally:
        conn.close()


@app.route("/documents/<int:document_id>", methods=["DELETE"])
def delete_document(document_id: int):
    """
    Remove a document, its stored chunks, and vector index.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
      
        cursor.execute("SELECT id FROM chunks WHERE document_id = ?", (document_id,))
        chunk_ids = [r["id"] for r in cursor.fetchall()]

        for cid in chunk_ids:
            try:
                cursor.execute("DELETE FROM vec_chunks WHERE chunk_id = ?", (cid,))
            except Exception:
                pass

        cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
       
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"detail": "Document not found"}), 404

        return jsonify({
            "success": True,
            "message": f"Document {document_id} and associated chunks deleted"
        }), 200
    finally:
        conn.close()


@app.route("/chat", methods=["POST"])
def chat():
    """
    Retrieval + Structured Generation + Server-Side Validation:
    1. Search top-k chunks with labeled context
    2. Prompt LLM to output structured answer + citations
    3. Server-side validation against SQLite chunks
    4. Store turn in chat_history
    """
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "")).strip() or str(uuid.uuid4())
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({"detail": "Message cannot be empty"}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO chat_history (session_id, role, content)
            VALUES (?, 'user', ?)
        """, (session_id, message))
        conn.commit()

        cursor.execute("""
            SELECT role, content
            FROM chat_history
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT 6
        """, (session_id,))
        past_turns = [{"role": r["role"], "content": r["content"]} for r in cursor.fetchall()]

        retrieved_chunks = vector_search_service.search_chunks(message, top_k=5)
        retrieved_chunk_ids = [c["chunk_id"] for c in retrieved_chunks]

        user_prompt = build_user_prompt(message, retrieved_chunks, past_turns)

        raw_output = llm_provider.generate_cited_answer(SYSTEM_PROMPT, user_prompt)
        raw_answer = raw_output.get("answer", "No answer generated.")
        raw_citations = raw_output.get("citations", [])

        grounded, validated_citations, warning = citation_validator.validate_citations(
            raw_citations=raw_citations,
            retrieved_chunk_ids=retrieved_chunk_ids,
            db_conn=conn
        )

        citations_json_str = json.dumps([c.model_dump() for c in validated_citations])
        cursor.execute("""
            INSERT INTO chat_history (session_id, role, content, citations_json, grounded)
            VALUES (?, 'assistant', ?, ?, ?)
        """, (session_id, raw_answer, citations_json_str, 1 if grounded else 0))
        conn.commit()

        return jsonify({
            "answer": raw_answer,
            "citations": [c.model_dump() for c in validated_citations],
            "grounded": grounded,
            "warning": warning
        }), 200
    finally:
        conn.close()


@app.route("/chunks/<int:chunk_id>", methods=["GET"])
def get_chunk_detail(chunk_id: int):
    """
    Fetch full chunk detail + metadata (used by frontend citation chips).
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.id,
                c.document_id,
                d.filename AS source_file,
                d.file_type,
                c.chunk_index,
                c.chunk_text,
                c.page_number,
                c.line_or_row_range,
                c.char_start,
                c.char_end
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.id = ?
        """, (chunk_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"detail": "Chunk not found"}), 404

        return jsonify({
            "id": row["id"],
            "document_id": row["document_id"],
            "source_file": row["source_file"],
            "file_type": row["file_type"],
            "chunk_index": row["chunk_index"],
            "chunk_text": row["chunk_text"],
            "page_number": row["page_number"],
            "line_or_row_range": row["line_or_row_range"],
            "char_start": row["char_start"],
            "char_end": row["char_end"]
        }), 200
    finally:
        conn.close()


@app.route("/chat/<session_id>/history", methods=["GET"])
def get_chat_history(session_id: str):
    """
    Retrieve past conversation turns with validated citations.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, role, content, citations_json, grounded, created_at
            FROM chat_history
            WHERE session_id = ?
            ORDER BY id ASC
        """, (session_id,))
        rows = cursor.fetchall()

        result = []
        for r in rows:
            cites = []
            if r["citations_json"]:
                try:
                    cites = json.loads(r["citations_json"])
                except Exception:
                    cites = []

            result.append({
                "id": r["id"],
                "session_id": r["session_id"],
                "role": r["role"],
                "content": r["content"],
                "citations": cites,
                "grounded": bool(r["grounded"]) if r["grounded"] is not None else None,
                "created_at": str(r["created_at"])
            })
        return jsonify(result), 200
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
