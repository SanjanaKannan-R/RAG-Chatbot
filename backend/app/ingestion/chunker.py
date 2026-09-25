import os
from typing import List
from app.models import RawChunk
from app.ingestion.txt_loader import load_txt
from app.ingestion.pdf_loader import load_pdf
from app.ingestion.csv_loader import load_csv

def process_file(file_path: str, filename: str) -> List[RawChunk]:
    """
    Inspects file extension and routes to appropriate loader.
    Supports .pdf, .txt, and .csv.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext == ".csv":
        return load_csv(file_path)
    elif ext in [".txt", ".md", ".log"]:
        return load_txt(file_path)
    else:
        # Default fallback to text loader
        return load_txt(file_path)
