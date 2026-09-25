import os
import io
import uuid
import tempfile
import pytest

# Configure environment for end-to-end test with Flask
os.environ["DATABASE_PATH"] = os.path.join(tempfile.gettempdir(), f"flask_e2e_{uuid.uuid4().hex}.db")
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["LLM_PROVIDER"] = "openai"
os.environ["OPENAI_API_KEY"] = "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"
os.environ["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"
os.environ["OPENAI_MODEL"] = "openai/gpt-oss-120b"

from app.main import app
from app.db.session import init_db, get_db_connection

init_db(os.environ["DATABASE_PATH"], embedding_dim=384)
client = app.test_client()

SAMPLE_PDF_BYTES = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length 85 >>
stream
BT
/F1 14 Tf
50 700 Td
(Invoice 482 for ACME Corp. Total: 5400 dollars. Due on Oct 15.) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000228 00000 n 
0000000301 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
436
%%EOF
"""

def test_step10_end_to_end_verification():
    print("\n--- STEP 10: FLASK END-TO-END VERIFICATION TEST ---")

    # 1. Upload PDF with known content
    upload_data = {
        "file": (io.BytesIO(SAMPLE_PDF_BYTES), "invoice_2024.pdf")
    }
    upload_resp = client.post("/documents/upload", data=upload_data, content_type="multipart/form-data")
    assert upload_resp.status_code == 200, upload_resp.get_data(as_text=True)
    doc_data = upload_resp.get_json()
    assert doc_data["status"] == "ready"
    assert doc_data["num_chunks"] >= 1
    doc_id = doc_data["id"]
    print(f"Step 10.1: Uploaded 'invoice_2024.pdf' as document ID {doc_id} with {doc_data['num_chunks']} chunk(s).")

    # 2. Ask a question answered by the PDF
    session_id = f"flask-e2e-session-{uuid.uuid4()}"
    query = "What is the total amount due on invoice 482 and when is it due?"
    print(f"Step 10.2: Sending query: '{query}'")

    chat_resp = client.post("/chat", json={"session_id": session_id, "message": query})
    assert chat_resp.status_code == 200, chat_resp.get_data(as_text=True)
    chat_result = chat_resp.get_json()

    print(f"Step 10.3: Received answer: {chat_result['answer']}")
    print(f"  Grounded status: {chat_result['grounded']}")
    print(f"  Citations count: {len(chat_result['citations'])}")

    # 3. Assertions on grounding and citations
    assert chat_result["grounded"] is True, "Expected answer to be grounded in the PDF document"
    assert len(chat_result["citations"]) > 0, "Expected at least one valid citation"

    citation = chat_result["citations"][0]
    cited_chunk_id = citation["chunk_id"]
    assert citation["source_file"] == "invoice_2024.pdf"

    # 4. MANUALLY & PROGRAMMATICALLY VERIFY CHUNK IN SQLITE DATABASE
    conn = get_db_connection(os.environ["DATABASE_PATH"])
    cur = conn.cursor()
    cur.execute("SELECT id, document_id, chunk_text, page_number FROM chunks WHERE id = ?", (cited_chunk_id,))
    stored_chunk = cur.fetchone()
    conn.close()

    assert stored_chunk is not None, f"Cited chunk_id {cited_chunk_id} not found in SQLite database!"
    stored_text = stored_chunk["chunk_text"]
    print(f"Step 10.4: AUTHORITATIVE SQLITE VERIFICATION:")
    print(f"  Cited chunk_id: {stored_chunk['id']}")
    print(f"  Stored literal text: '{stored_text}'")
    print(f"  Page number: {stored_chunk['page_number']}")

    # Verify that the literal text in SQLite actually contains the ground truth facts
    assert "5400" in stored_text, "Verification failed: '$5400' not found in stored chunk text"
    assert "Oct 15" in stored_text, "Verification failed: 'Oct 15' not found in stored chunk text"
    assert "Invoice 482" in stored_text, "Verification failed: 'Invoice 482' not found in stored chunk text"

    # 5. Check ungrounded question behavior
    ungrounded_query = "What is the population of Mars in the year 3000?"
    print(f"\nStep 10.5: Testing ungrounded question: '{ungrounded_query}'")
    un_resp = client.post("/chat", json={"session_id": session_id, "message": ungrounded_query})
    assert un_resp.status_code == 200
    un_result = un_resp.get_json()
    print(f"  Ungrounded answer: {un_result['answer']}")
    print(f"  Grounded status: {un_result['grounded']}")
    assert un_result["grounded"] is False, "Expected grounded: False for ungrounded question"
    assert len(un_result["citations"]) == 0, "Expected empty citations for ungrounded question"

    print("\nSTEP 10 COMPLETE: Flask End-to-end PDF upload, grounding, and literal SQLite verification passed!")

if __name__ == "__main__":
    test_step10_end_to_end_verification()
