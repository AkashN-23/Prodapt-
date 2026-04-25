"""
scripts/ingest.py
-----------------
Chunk annual report PDFs and embed them into a local ChromaDB instance.
Usage: python scripts/ingest.py
"""

import os
import sys
import hashlib
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pypdf import PdfReader
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

PDF_DIR       = Path("./data/pdfs")
STORE_PATH    = os.getenv("VECTOR_STORE_PATH", "./data/chroma_store")
EMBED_MODEL   = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION    = "annual_reports"
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 120

console = Console()


def extract_pages(pdf_path: Path) -> list[tuple[str, int]]:
    """Return list of (page_text, page_number) for every page in the PDF."""
    reader = PdfReader(str(pdf_path))
    return [(page.extract_text() or "", i + 1) for i, page in enumerate(reader.pages)]


def recursive_split(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text recursively on paragraph → sentence → word boundaries."""
    if len(text) <= size:
        return [text] if text.strip() else []

    for sep in ["\n\n", "\n", ". ", " "]:
        mid = len(text) // 2
        idx = text.rfind(sep, overlap, mid + size)
        if idx != -1:
            left  = text[: idx + len(sep)].strip()
            right = text[max(0, idx + len(sep) - overlap) :].strip()
            return recursive_split(left, size, overlap) + recursive_split(right, size, overlap)

    return [text[:size], text[size - overlap:]]


def chunk_id(source: str, page: int, chunk_idx: int) -> str:
    raw = f"{source}:{page}:{chunk_idx}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def main() -> None:
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        console.print(f"[red]No PDFs found in {PDF_DIR}. Add your annual report PDFs and retry.[/red]")
        sys.exit(1)

    embed_fn   = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    db         = chromadb.PersistentClient(path=STORE_PATH)
    collection = db.get_or_create_collection(COLLECTION, embedding_function=embed_fn)

    console.print(f"\n[bold cyan]⬡ stnapt.ai  ingest[/bold cyan]  {len(pdf_files)} PDF(s) → {STORE_PATH}\n")

    total_chunks = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} pages"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        for pdf_path in pdf_files:
            pages = extract_pages(pdf_path)
            task  = progress.add_task(f"  {pdf_path.name}", total=len(pages))

            for page_text, page_num in pages:
                chunks = recursive_split(page_text)
                if not chunks:
                    progress.advance(task)
                    continue

                ids      = [chunk_id(pdf_path.name, page_num, i) for i in range(len(chunks))]
                metadatas = [
                    {"source_file": pdf_path.name, "page_number": page_num, "chunk_index": i}
                    for i in range(len(chunks))
                ]
                collection.upsert(documents=chunks, ids=ids, metadatas=metadatas)
                total_chunks += len(chunks)
                progress.advance(task)

    console.print(f"\n[green]✓[/green] Indexed [bold]{total_chunks}[/bold] chunks from {len(pdf_files)} PDF(s).")
    console.print(f"  Collection [bold]{COLLECTION}[/bold] ready at [dim]{STORE_PATH}[/dim]\n")


if __name__ == "__main__":
    main()
