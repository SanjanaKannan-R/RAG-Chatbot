import os
import sqlite3
from typing import List, Optional
import sqlite_vec

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

def serialize_vector(vector: List[float]) -> bytes:
    """Serializes a list of floats into sqlite-vec float32 binary format."""
    return sqlite_vec.serialize_float32(vector)

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Creates and returns a SQLite connection with sqlite-vec loaded,
    WAL mode, and Row factory configured.
    """
    path = db_path or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
    conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # Load sqlite-vec extension
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    
    # SQLite optimizations
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    
    return conn

def init_db(db_path: Optional[str] = None, embedding_dim: int = 384) -> None:
    """
    Initializes the database schema and creates the sqlite-vec virtual table.
    """
    conn = get_db_connection(db_path)
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        
        # Create or ensure vec_chunks virtual table for fast ANN cosine search
        conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
                chunk_id INTEGER PRIMARY KEY,
                embedding float[{embedding_dim}] distance_metric=cosine
            );
        """)
        conn.commit()
    finally:
        conn.close()
