from typing import List, Tuple
import os
from app.models import RawChunk

def _extract_pages_pypdf(file_path: str) -> List[Tuple[int, str]]:
    import pypdf
    pages = []
    reader = pypdf.PdfReader(file_path)
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append((idx, text))
    return pages

def _extract_pages_pdfplumber(file_path: str) -> List[Tuple[int, str]]:
    import pdfplumber
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append((idx, text))
    return pages

def load_pdf(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[RawChunk]:
    """
    Extracts text from a PDF file preserving page numbers and offsets,
    splitting each page or continuous text using LangChain RecursiveCharacterTextSplitter.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # Attempt pdfplumber first, fallback to pypdf
    try:
        pages = _extract_pages_pdfplumber(file_path)
    except Exception:
        pages = _extract_pages_pypdf(file_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    raw_chunks: List[RawChunk] = []
    chunk_index = 0
    cumulative_char_offset = 0

    for page_num, page_text in pages:
        cleaned_text = page_text.strip()
        if not cleaned_text:
            continue

        page_chunks = splitter.split_text(cleaned_text)
        search_start = 0

        for text_chunk in page_chunks:
            local_start = cleaned_text.find(text_chunk, search_start)
            if local_start == -1:
                local_start = search_start
            local_end = local_start + len(text_chunk)
            search_start = max(search_start, local_start + 1)

            global_start = cumulative_char_offset + local_start
            global_end = cumulative_char_offset + local_end

            # Calculate line range within this page
            page_lines = cleaned_text[:local_end].splitlines()
            start_line = len(cleaned_text[:local_start].splitlines())
            start_line = max(1, start_line)
            end_line = len(page_lines)

            line_range = f"page {page_num}, lines {start_line}-{end_line}" if start_line != end_line else f"page {page_num}, line {start_line}"

            raw_chunks.append(RawChunk(
                chunk_index=chunk_index,
                chunk_text=text_chunk,
                page_number=page_num,
                line_or_row_range=line_range,
                char_start=global_start,
                char_end=global_end
            ))
            chunk_index += 1

        cumulative_char_offset += len(page_text) + 2

    return raw_chunks
