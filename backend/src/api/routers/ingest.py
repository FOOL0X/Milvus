from fastapi import APIRouter, UploadFile, File, HTTPException
from src.models.schemas import IngestResponse
from src.services.ingest import ingest_service
from src.core.vector_store import vector_store_service
import tempfile
import os
from pathlib import Path

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestResponse)
async def ingest_documents(
    file: UploadFile = File(...),
    collection_name: str = "customer_service_kb",
    category: str = "general"
):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            metadata = {"category": category}
            result = ingest_service.ingest_file(
                file_path=tmp_path,
                collection_name=collection_name,
                metadata=metadata
            )

            return IngestResponse(**result)

        finally:
            os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/directory")
async def ingest_directory(
    directory_path: str,
    collection_name: str = "customer_service_kb"
):
    try:
        if not Path(directory_path).exists():
            raise HTTPException(status_code=400, detail=f"Directory not found: {directory_path}")

        result = ingest_service.ingest_directory(
            directory_path=directory_path,
            collection_name=collection_name
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
