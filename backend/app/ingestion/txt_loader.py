import re
from typing import List
from app.models import RawChunk

def load_txt(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[RawChunk]:
    """
    Loads a .txt file, tracking exact line numbers and character offsets
    for each generated chunk.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        full_text = f.read()

    if not full_text.strip():
        return []

    # Map line number to character offset range
    lines = full_text.splitlines(keepends=True)
    line_offsets = []
    current_char = 0
    for line_idx, line in enumerate(lines, start=1):
        line_start = current_char
        current_char += len(line)
        line_offsets.append((line_idx, line_start, current_char))

    def get_line_range(c_start: int, c_end: int) -> str:
        start_line = 1
        end_line = len(line_offsets)
        for l_num, l_s, l_e in line_offsets:
            if l_s <= c_start < l_e:
                start_line = l_num
                break
        for l_num, l_s, l_e in reversed(line_offsets):
            if c_end > l_s:
                end_line = l_num
                break
        if start_line == end_line:
            return f"line {start_line}"
        return f"lines {start_line}-{end_line}"

    # Use LangChain RecursiveCharacterTextSplitter with character tracking
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    docs = splitter.split_text(full_text)
    raw_chunks: List[RawChunk] = []
    search_start = 0
    
    for idx, chunk_text in enumerate(docs):
        # Locate exact position in full text
        char_start = full_text.find(chunk_text, search_start)
        if char_start == -1:
            # Fallback if whitespace variation
            char_start = full_text.find(chunk_text[:30], search_start)
            if char_start == -1:
                char_start = search_start
        char_end = char_start + len(chunk_text)
        search_start = max(search_start, char_start + 1)
        
        line_range = get_line_range(char_start, char_end)
        
        raw_chunks.append(RawChunk(
            chunk_index=idx,
            chunk_text=chunk_text,
            page_number=1,
            line_or_row_range=line_range,
            char_start=char_start,
            char_end=char_end
        ))
        
    return raw_chunks
