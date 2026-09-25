export interface CitationItem {
  chunk_id: number;
  quoted_snippet: string;
  source_file?: string;
  page_number?: number | null;
  line_or_row_range?: string | null;
  char_start?: number | null;
  char_end?: number | null;
  chunk_text?: string | null;
}

export interface DocumentItem {
  id: number;
  filename: string;
  file_type: string;
  uploaded_at: string;
  num_chunks: number;
  status: 'processing' | 'ready' | 'failed' | string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: CitationItem[];
  grounded?: boolean;
  warning?: string | null;
  timestamp: string;
}

export interface ChunkDetail {
  id: number;
  document_id: number;
  source_file: string;
  file_type: string;
  chunk_index: number;
  chunk_text: string;
  page_number?: number | null;
  line_or_row_range?: string | null;
  char_start?: number | null;
  char_end?: number | null;
}
