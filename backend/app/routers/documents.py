from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ChunkOut, DocumentOut
from app.services import documents as service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> DocumentOut:
    """Sube un documento: guarda el fichero original y lo registra como `subido`."""
    filename = file.filename or "sin_nombre"
    doc = service.create_document(db, data=file.file, filename=filename)
    return DocumentOut.model_validate(doc)


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentOut]:
    return [DocumentOut.model_validate(d) for d in service.list_documents(db)]


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)) -> DocumentOut:
    doc = service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return DocumentOut.model_validate(doc)


@router.get("/{doc_id}/chunks", response_model=list[ChunkOut])
def list_chunks(doc_id: int, db: Session = Depends(get_db)) -> list[ChunkOut]:
    """Chunks de un documento, para inspeccionar el troceo."""
    if service.get_document(db, doc_id) is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return [ChunkOut.model_validate(c) for c in service.list_chunks(db, doc_id)]
