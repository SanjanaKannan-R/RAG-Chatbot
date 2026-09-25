from typing import List, Optional
from pydantic import BaseModel, Field

class RawChunk(BaseModel):
    chunk_index: int
    chunk_text: str
    page_number: Optional[int] = None
    line_or_row_range: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None

class DocumentItem(BaseModel):
    id: int
    filename: str
    file_type: str
    uploaded_at: str
    num_chunks: int
    status: str

class CitationItem(BaseModel):
    chunk_id: int
    quoted_snippet: str
    source_file: Optional[str] = None
    page_number: Optional[int] = None
    line_or_row_range: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    chunk_text: Optional[str] = None

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    answer: str
    citations: List[CitationItem]
    grounded: bool
    warning: Optional[str] = None

class ChunkDetailResponse(BaseModel):
    id: int
    document_id: int
    source_file: str
    file_type: str
    chunk_index: int
    chunk_text: str
    page_number: Optional[int] = None
    line_or_row_range: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None

class ChatMessageItem(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    citations: List[CitationItem] = Field(default_factory=list)
    grounded: Optional[bool] = None
    created_at: str
