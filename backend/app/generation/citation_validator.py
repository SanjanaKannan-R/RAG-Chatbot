import sqlite3
import re
from typing import List, Dict, Any, Tuple, Optional
from app.db.session import get_db_connection
from app.models import CitationItem

class CitationValidator:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def validate_citations(
        self,
        raw_citations: List[Dict[str, Any]],
        retrieved_chunk_ids: List[int],
        db_conn: Optional[sqlite3.Connection] = None
    ) -> Tuple[bool, List[CitationItem], Optional[str]]:
        """
        Server-side validation:
        1. Reject any citation whose chunk_id was NOT in the retrieved set for this query.
        2. Verify existence of chunk_id in the SQLite chunks table.
        3. Query true SQLite metadata (source_file, page, offsets, chunk_text) - don't trust LLM.
        4. Check and locate quoted_snippet within chunk_text for exact highlighting.
        5. Return grounded: bool, validated_citations, warning: Optional[str].
        """
        if not raw_citations:
            return False, [], "No citations provided in the response."

        retrieved_set = set(retrieved_chunk_ids)
        conn = db_conn or get_db_connection(self.db_path)
        should_close = db_conn is None

        validated: List[CitationItem] = []
        hallucinated_count = 0

        try:
            cursor = conn.cursor()

            for item in raw_citations:
                try:
                    cid = int(item.get("chunk_id"))
                except (ValueError, TypeError):
                    hallucinated_count += 1
                    continue

                # Rule 1: Must be in the retrieved set for this turn
                if cid not in retrieved_set:
                    hallucinated_count += 1
                    continue

                # Rule 2 & 3: Look up authoritative chunk & document metadata in SQLite
                cursor.execute("""
                    SELECT 
                        c.id AS chunk_id,
                        c.document_id,
                        d.filename AS source_file,
                        c.page_number,
                        c.line_or_row_range,
                        c.char_start,
                        c.char_end,
                        c.chunk_text
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE c.id = ?
                """, (cid,))
                row = cursor.fetchone()
                if not row:
                    hallucinated_count += 1
                    continue

                chunk_text = row["chunk_text"]
                quoted_snippet = str(item.get("quoted_snippet") or "").strip()

                # Rule 4: Match and locate snippet within chunk_text
                # Try exact match first, then normalized whitespace match
                snippet_start = -1
                snippet_end = -1
                if quoted_snippet:
                    pos = chunk_text.find(quoted_snippet)
                    if pos != -1:
                        snippet_start = pos
                        snippet_end = pos + len(quoted_snippet)
                    else:
                        # Whitespace normalized match
                        norm_snippet = re.sub(r'\s+', ' ', quoted_snippet).lower()
                        norm_chunk = re.sub(r'\s+', ' ', chunk_text).lower()
                        pos = norm_chunk.find(norm_snippet)
                        if pos != -1:
                            snippet_start = pos
                            snippet_end = pos + len(quoted_snippet)

                # If snippet is completely empty or missing, fallback to chunk preview
                if not quoted_snippet:
                    quoted_snippet = chunk_text[:120] + ("..." if len(chunk_text) > 120 else "")

                # Calculate document-level offsets if available
                base_char_start = row["char_start"] or 0
                exact_doc_char_start = (base_char_start + snippet_start) if snippet_start != -1 else base_char_start
                exact_doc_char_end = (base_char_start + snippet_end) if snippet_end != -1 else (row["char_end"] or base_char_start + len(chunk_text))

                validated.append(CitationItem(
                    chunk_id=cid,
                    quoted_snippet=quoted_snippet,
                    source_file=row["source_file"],
                    page_number=row["page_number"],
                    line_or_row_range=row["line_or_row_range"],
                    char_start=exact_doc_char_start,
                    char_end=exact_doc_char_end,
                    chunk_text=chunk_text
                ))

        finally:
            if should_close:
                conn.close()

        warning = None
        if hallucinated_count > 0:
            warning = f"Stripped {hallucinated_count} unverified citation(s) from LLM output."

        grounded = len(validated) > 0
        if not grounded:
            warning = "This answer could not be grounded in your documents."

        return grounded, validated, warning
