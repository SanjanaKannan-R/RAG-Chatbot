import os
from typing import Dict, Any, Optional
from app.db.session import get_db_connection, serialize_vector
from app.ingestion.chunker import process_file
from app.retrieval.embeddings import BaseEmbeddingProvider, get_embedding_provider

class IngestionService:
    def __init__(self, db_path: Optional[str] = None, embedding_provider: Optional[BaseEmbeddingProvider] = None):
        self.db_path = db_path
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def ingest_file(self, file_path: str, original_filename: str) -> Dict[str, Any]:
        """
        Runs the complete ingestion pipeline:
        1. Creates document entry with status='processing'
        2. Chunks file with exact location tracking
        3. Generates vector embeddings
        4. Inserts chunks + embeddings into SQLite and vec0 virtual table
        5. Updates document status to 'ready'
        """
        ext = os.path.splitext(original_filename)[1].lower().lstrip(".")
        if ext not in ["pdf", "txt", "csv", "md", "log"]:
            ext = "txt"

        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # 1. Insert document record
        cursor.execute(
            "INSERT INTO documents (filename, file_type, num_chunks, status) VALUES (?, ?, 0, 'processing')",
            (original_filename, ext)
        )
        doc_id = cursor.lastrowid
        conn.commit()

        try:
            # 2. Extract and chunk
            raw_chunks = process_file(file_path, original_filename)
            if not raw_chunks:
                cursor.execute("UPDATE documents SET status = 'ready', num_chunks = 0 WHERE id = ?", (doc_id,))
                conn.commit()
                return {
                    "document_id": doc_id,
                    "filename": original_filename,
                    "file_type": ext,
                    "num_chunks": 0,
                    "status": "ready"
                }

            # 3. Batch generate embeddings
            texts = [chunk.chunk_text for chunk in raw_chunks]
            embeddings = self.embedding_provider.embed_batch(texts)

            # 4. Insert chunks into chunks table and vec_chunks
            for raw_chunk, emb in zip(raw_chunks, embeddings):
                serialized_emb = serialize_vector(emb)
                cursor.execute("""
                    INSERT INTO chunks (
                        document_id, chunk_index, chunk_text,
                        page_number, line_or_row_range, char_start, char_end, embedding
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    raw_chunk.chunk_index,
                    raw_chunk.chunk_text,
                    raw_chunk.page_number,
                    raw_chunk.line_or_row_range,
                    raw_chunk.char_start,
                    raw_chunk.char_end,
                    serialized_emb
                ))
                chunk_id = cursor.lastrowid

                # Index in vec_chunks virtual table if present
                try:
                    cursor.execute(
                        "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
                        (chunk_id, serialized_emb)
                    )
                except Exception:
                    # vec_chunks might not exist if virtual table isn't created yet
                    pass

            # 5. Mark ready
            cursor.execute(
                "UPDATE documents SET status = 'ready', num_chunks = ? WHERE id = ?",
                (len(raw_chunks), doc_id)
            )
            conn.commit()

            return {
                "document_id": doc_id,
                "filename": original_filename,
                "file_type": ext,
                "num_chunks": len(raw_chunks),
                "status": "ready"
            }

        except Exception as e:
            conn.rollback()
            cursor.execute("UPDATE documents SET status = 'failed' WHERE id = ?", (doc_id,))
            conn.commit()
            raise e
        finally:
            conn.close()
