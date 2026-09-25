import os
import io
import uuid
import tempfile
import pytest

# Configure environment for Flask test
os.environ["DATABASE_PATH"] = os.path.join(tempfile.gettempdir(), f"flask_api_{uuid.uuid4().hex}.db")
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["LLM_PROVIDER"] = "rule"

from app.main import app
from app.db.session import init_db

init_db(os.environ["DATABASE_PATH"], embedding_dim=384)
client = app.test_client()

def test_flask_api_endpoints_flow():
    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["framework"] == "Flask"
    print("Flask Health check endpoint OK.")

    # 2. Upload document
    sample_content = (
        "Server Deployment Specifications 2026\n"
        "The production database runs on port 5432 with replication enabled.\n"
        "Backups are performed daily at 02:00 UTC and retained for 30 days.\n"
    )
    upload_data = {
        "file": (io.BytesIO(sample_content.encode("utf-8")), "deployment_spec.txt")
    }
    upload_res = client.post("/documents/upload", data=upload_data, content_type="multipart/form-data")
    assert upload_res.status_code == 200, upload_res.get_data(as_text=True)
    doc_info = upload_res.get_json()
    assert doc_info["filename"] == "deployment_spec.txt"
    assert doc_info["status"] == "ready"
    doc_id = doc_info["id"]
    print(f"Flask Uploaded document ID: {doc_id}")

    # 3. List documents
    docs_res = client.get("/documents")
    assert docs_res.status_code == 200
    docs = docs_res.get_json()
    assert len(docs) >= 1
    assert any(d["id"] == doc_id for d in docs)
    print("Flask List documents endpoint OK.")

    # 4. Chat endpoint
    session_id = f"flask-session-{uuid.uuid4()}"
    chat_payload = {
        "session_id": session_id,
        "message": "When are backups performed?"
    }
    chat_res = client.post("/chat", json=chat_payload)
    assert chat_res.status_code == 200, chat_res.get_data(as_text=True)
    chat_data = chat_res.get_json()
    print("Flask Chat response:", chat_data)
    assert "answer" in chat_data
    assert "grounded" in chat_data
    assert chat_data["grounded"] is True
    assert len(chat_data["citations"]) > 0

    chunk_id = chat_data["citations"][0]["chunk_id"]
    assert chunk_id > 0
    assert chat_data["citations"][0]["source_file"] == "deployment_spec.txt"

    # 5. Get chunk detail
    chunk_res = client.get(f"/chunks/{chunk_id}")
    assert chunk_res.status_code == 200
    chunk_detail = chunk_res.get_json()
    assert chunk_detail["id"] == chunk_id
    assert chunk_detail["source_file"] == "deployment_spec.txt"
    assert "Backups are performed daily" in chunk_detail["chunk_text"]
    print("Flask Chunk detail endpoint OK.")

    # 6. Chat history
    history_res = client.get(f"/chat/{session_id}/history")
    assert history_res.status_code == 200
    history = history_res.get_json()
    assert len(history) == 2  # user + assistant
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert len(history[1]["citations"]) > 0
    print("Flask Chat history endpoint OK.")

    # 7. Delete document
    del_res = client.delete(f"/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # Verify document is gone
    docs_after = client.get("/documents").get_json()
    assert not any(d["id"] == doc_id for d in docs_after)
    print("Flask Delete document endpoint OK.")

    print("\nStep 8 PASSED: All Flask endpoints verified end-to-end!")

if __name__ == "__main__":
    test_flask_api_endpoints_flow()
