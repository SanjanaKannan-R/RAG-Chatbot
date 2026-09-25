import sqlite3
from typing import List, Dict, Any, Optional
from app.db.session import serialize_vector, get_db_connection
from app.retrieval.embeddings import BaseEmbeddingProvider, get_embedding_provider

class VectorSearchService:
    def __init__(self, db_path: Optional[str] = None, embedding_provider: Optional[BaseEmbeddingProvider] = None):
        self.db_path = db_path
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def search_chunks(self, query: str, top_k: int = 5, document_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Embeds the query and performs cosine similarity search via sqlite-vec,
        joining chunks with documents to return full verified metadata.
        """
        query_vector = self.embedding_provider.embed_text(query)
        serialized_query = serialize_vector(query_vector)

        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()

            # Attempt search using vec0 virtual table
            try:
                if document_id:
                    query_sql = """
                        SELECT 
                            c.id AS chunk_id,
                            c.document_id,
                            d.filename AS source_file,
                            d.file_type,
                            c.chunk_index,
                            c.chunk_text,
                            c.page_number,
                            c.line_or_row_range,
                            c.char_start,
                            c.char_end,
                            v.distance
                        FROM vec_chunks v
                        JOIN chunks c ON c.id = v.chunk_id
                        JOIN documents d ON d.id = c.document_id
                        WHERE v.embedding MATCH ?
                          AND k = ?
                          AND c.document_id = ?
                        ORDER BY v.distance ASC
                    """
                    cursor.execute(query_sql, (serialized_query, top_k * 2, document_id))
                else:
                    query_sql = """
                        SELECT 
                            c.id AS chunk_id,
                            c.document_id,
                            d.filename AS source_file,
                            d.file_type,
                            c.chunk_index,
                            c.chunk_text,
                            c.page_number,
                            c.line_or_row_range,
                            c.char_start,
                            c.char_end,
                            v.distance
                        FROM vec_chunks v
                        JOIN chunks c ON c.id = v.chunk_id
                        JOIN documents d ON d.id = c.document_id
                        WHERE v.embedding MATCH ?
                          AND k = ?
                        ORDER BY v.distance ASC
                    """
                    cursor.execute(query_sql, (serialized_query, top_k))
                rows = cursor.fetchall()
            except Exception:
                # Direct scan fallback using vec_distance_cosine
                doc_filter = "AND c.document_id = ?" if document_id else ""
                fallback_sql = f"""
                    SELECT 
                        c.id AS chunk_id,
                        c.document_id,
                        d.filename AS source_file,
                        d.file_type,
                        c.chunk_index,
                        c.chunk_text,
                        c.page_number,
                        c.line_or_row_range,
                        c.char_start,
                        c.char_end,
                        vec_distance_cosine(c.embedding, ?) AS distance
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE d.status = 'ready' {doc_filter}
                    ORDER BY distance ASC
                    LIMIT ?
                """
                params = (serialized_query, document_id, top_k) if document_id else (serialized_query, top_k)
                cursor.execute(fallback_sql, params)
                rows = cursor.fetchall()

            results = []
            for row in rows[:top_k]:
                dist = float(row["distance"])
                results.append({
                    "chunk_id": int(row["chunk_id"]),
                    "document_id": int(row["document_id"]),
                    "source_file": row["source_file"],
                    "file_type": row["file_type"],
                    "chunk_index": int(row["chunk_index"]),
                    "chunk_text": row["chunk_text"],
                    "page_number": row["page_number"],
                    "line_or_row_range": row["line_or_row_range"],
                    "char_start": row["char_start"],
                    "char_end": row["char_end"],
                    "distance": dist,
                    "similarity": round(max(0.0, 1.0 - dist), 4)
                })
            return results
        finally:
            conn.close()
