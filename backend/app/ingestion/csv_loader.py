from typing import List
import pandas as pd
from app.models import RawChunk

def load_csv(file_path: str, rows_per_chunk: int = 20) -> List[RawChunk]:
    """
    Loads a CSV file using pandas, chunking by row groups (e.g. 20 rows).
    Headers are included in every chunk to preserve semantic context.
    Tracks exact row ranges (e.g. 'rows 1-20', 'rows 21-40').
    """
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding="latin1")

    if df.empty:
        return []

    raw_chunks: List[RawChunk] = []
    total_rows = len(df)
    columns_str = ", ".join([str(col) for col in df.columns])

    # Also read raw file text to estimate character offsets
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        full_content = f.read()
    raw_lines = full_content.splitlines(keepends=True)
    header_offset = len(raw_lines[0]) if raw_lines else 0

    chunk_idx = 0
    for start_row in range(0, total_rows, rows_per_chunk):
        end_row = min(start_row + rows_per_chunk, total_rows)
        slice_df = df.iloc[start_row:end_row]

        # Format chunk with clear tabular / markdown representation
        # plus explicit column names
        table_text = slice_df.to_string(index=False)
        chunk_text = f"Columns: {columns_str}\nRows {start_row + 1} to {end_row} (of {total_rows}):\n{table_text}"

        # Estimate char offsets in original CSV
        line_start_idx = start_row + 1  # 1-indexed (skipping header)
        line_end_idx = end_row + 1
        
        char_start = sum(len(raw_lines[i]) for i in range(min(line_start_idx, len(raw_lines))))
        char_end = sum(len(raw_lines[i]) for i in range(min(line_end_idx, len(raw_lines))))

        raw_chunks.append(RawChunk(
            chunk_index=chunk_idx,
            chunk_text=chunk_text,
            page_number=(start_row // rows_per_chunk) + 1,
            line_or_row_range=f"rows {start_row + 1}-{end_row}",
            char_start=char_start,
            char_end=char_end
        ))
        chunk_idx += 1

    return raw_chunks
