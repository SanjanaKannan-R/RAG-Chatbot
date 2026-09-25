import sqlite3
import numpy as np
from app.db.session import init_db, get_db_connection, serialize_vector

def test_sqlite_vec_setup(tmp_path=None):
    db_file = ":memory:"
    conn = get_db_connection(db_file)
    
    # Initialize tables
    with open("backend/app/db/schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
        
    conn.execute("""
        CREATE VIRTUAL TABLE vec_chunks USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding float[4] distance_metric=cosine
        );
    """)
    
    # Insert a dummy document
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (filename, file_type, num_chunks, status) VALUES (?, ?, ?, ?)",
        ("test.txt", "txt", 2, "ready")
    )
    doc_id = cursor.lastrowid
    
    # Insert two chunks with known vectors
    # v1: [1.0, 0.0, 0.0, 0.0]
    # v2: [0.0, 1.0, 0.0, 0.0]
    v1 = [1.0, 0.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0, 0.0]
    
    cursor.execute("""
        INSERT INTO chunks (document_id, chunk_index, chunk_text, page_number, line_or_row_range, char_start, char_end, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc_id, 0, "Chunk 1: Machine learning algorithms", 1, "1-5", 0, 36, serialize_vector(v1)))
    chunk1_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO chunks (document_id, chunk_index, chunk_text, page_number, line_or_row_range, char_start, char_end, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc_id, 1, "Chunk 2: Cooking delicious pasta", 1, "6-10", 37, 70, serialize_vector(v2)))
    chunk2_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)", (chunk1_id, serialize_vector(v1)))
    cursor.execute("INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)", (chunk2_id, serialize_vector(v2)))
    conn.commit()
    
    # Query vector: close to v1: [0.95, 0.05, 0.0, 0.0]
    query_vec = [0.95, 0.05, 0.0, 0.0]
    
    # Test vec0 virtual table search
    cursor.execute("""
        SELECT chunk_id, distance
        FROM vec_chunks
        WHERE embedding MATCH ?
          AND k = 2
        ORDER BY distance
    """, (serialize_vector(query_vec),))
    
    results = cursor.fetchall()
    print("vec0 query results:", [(r["chunk_id"], r["distance"]) for r in results])
    assert len(results) == 2
    assert results[0]["chunk_id"] == chunk1_id, f"Expected chunk1_id ({chunk1_id}) to be top match, got {results[0]['chunk_id']}"
    
    # Also test cosine distance directly on chunks table
    cursor.execute("""
        SELECT id, chunk_text, vec_distance_cosine(embedding, ?) AS dist
        FROM chunks
        ORDER BY dist ASC
        LIMIT 2
    """, (serialize_vector(query_vec),))
    direct_results = cursor.fetchall()
    print("Direct cosine results:", [(r["id"], r["chunk_text"], r["dist"]) for r in direct_results])
    assert direct_results[0]["id"] == chunk1_id
    
    conn.close()
    print("Step 1 PASSED: SQLite schema + sqlite-vec insertion and cosine similarity search verified successfully!")

if __name__ == "__main__":
    test_sqlite_vec_setup()
