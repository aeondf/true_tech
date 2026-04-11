from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.file_processor import FileProcessor
from app.services.chunk_store import ChunkStore, get_chunk_store
from app.config import get_settings

router = APIRouter()
settings = get_settings()

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = "anonymous",
    chunk_store: ChunkStore = Depends(get_chunk_store),
):
    """
    Accept PDF / DOCX / TXT → extract text → split into chunks
    → embed via bge-m3 → store in pgvector.
    Returns file_id and chunk count.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}",
        )

    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_FILE_SIZE_MB} MB limit",
        )

    processor = FileProcessor()
    chunks = processor.extract_chunks(
        content=content,
        filename=file.filename or "upload",
        content_type=file.content_type or "",
    )

    file_id = await chunk_store.store(
        user_id=user_id,
        filename=file.filename or "upload",
        chunks=chunks,
    )

    return {"file_id": file_id, "chunks": len(chunks)}
