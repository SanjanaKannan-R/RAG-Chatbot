from typing import List, Dict, Any

SYSTEM_PROMPT = """You are a citation-grounded enterprise AI assistant.
Your absolute top priority is factual precision and verifiability.

Rules:
1. Every claim, fact, number, and statement in your answer MUST be grounded in the provided retrieved document chunks.
2. In your citations list, reference the exact `chunk_id` integer and provide the `quoted_snippet` (the verbatim phrase or sentence from that chunk that supports the claim).
3. Do NOT make up or hallucinate any `chunk_id`. Only cite chunk IDs that are explicitly labeled in the context below.
4. If the provided context does NOT contain sufficient information to answer the question, state honestly:
   "I cannot answer this based on the provided documents."
   and return an empty list for "citations".
5. You must respond with valid JSON strictly conforming to this JSON schema:
{
  "answer": "string containing the full synthesized answer",
  "citations": [
    {
      "chunk_id": 123,
      "quoted_snippet": "verbatim text snippet supporting the statement"
    }
  ]
}
"""

def format_context_chunks(chunks: List[Dict[str, Any]]) -> str:
    """
    Formats retrieved chunks with strict chunk_id labeling:
    [chunk_id: 482 | source: invoice_2024.pdf | page: 3]
    <chunk text>
    """
    if not chunks:
        return "No relevant documents found."

    formatted_blocks = []
    for c in chunks:
        cid = c.get("chunk_id") or c.get("id")
        source = c.get("source_file", "unknown")
        
        # Location tag: page or lines/rows
        loc_parts = []
        if c.get("page_number") is not None:
            loc_parts.append(f"page: {c['page_number']}")
        if c.get("line_or_row_range"):
            loc_parts.append(str(c["line_or_row_range"]))
            
        loc_str = " | " + ", ".join(loc_parts) if loc_parts else ""
        header = f"[chunk_id: {cid} | source: {source}{loc_str}]"
        block = f"{header}\n{c.get('chunk_text', '').strip()}"
        formatted_blocks.append(block)

    return "\n\n".join(formatted_blocks)

def build_user_prompt(query: str, chunks: List[Dict[str, Any]], conversation_history: List[Dict[str, str]] = None) -> str:
    context_str = format_context_chunks(chunks)
    
    history_str = ""
    if conversation_history:
        recent = conversation_history[-4:]  # last 2 turns
        hist_lines = []
        for h in recent:
            role = "User" if h.get("role") == "user" else "Assistant"
            hist_lines.append(f"{role}: {h.get('content', '')}")
        history_str = "Recent Conversation History:\n" + "\n".join(hist_lines) + "\n\n"

    return (
        f"{history_str}"
        f"Retrieved Document Context Chunks:\n"
        f"----------------------------------------\n"
        f"{context_str}\n"
        f"----------------------------------------\n\n"
        f"User Question: {query}\n\n"
        f"Provide your grounded answer with citations in the required JSON format."
    )
