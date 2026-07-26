from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_empresa_id, get_empresa_id_admin
from app.schemas import ChunkOut, DocumentAreasIn, DocumentOut
from app.services import documents as service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(
    file: UploadFile,
    area_ids: list[int] = Form(...),
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Sube un documento: guarda el fichero original y lo registra como `subido`.

    Solo admin de empresa (un `usuario` normal puede ver documentos, no subirlos).
    `area_ids` (campo de formulario) son las áreas de acceso; al menos una, de la empresa.
    """
    filename = file.filename or "sin_nombre"
    try:
        doc = service.create_document(
            db, data=file.file, filename=filename, empresa_id=empresa_id, area_ids=area_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentOut.model_validate(doc)


@router.put("/{doc_id}/areas", response_model=DocumentOut)
def set_areas(
    doc_id: int,
    body: DocumentAreasIn,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """Reemplaza las áreas de un documento. Solo admin de empresa."""
    doc = service.get_document(db, doc_id, empresa_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    try:
        service.set_document_areas(db, doc, body.area_ids, empresa_id)
        db.commit()
        db.refresh(doc)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentOut.model_validate(doc)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    empresa_id: int = Depends(get_empresa_id), db: Session = Depends(get_db)
) -> list[DocumentOut]:
    return [DocumentOut.model_validate(d) for d in service.list_documents(db, empresa_id)]


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    empresa_id: int = Depends(get_empresa_id),
    db: Session = Depends(get_db),
) -> DocumentOut:
    doc = service.get_document(db, doc_id, empresa_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return DocumentOut.model_validate(doc)


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    empresa_id: int = Depends(get_empresa_id_admin),
    db: Session = Depends(get_db),
) -> None:
    """Borra un documento subido por error. Solo admin de empresa."""
    if not service.delete_document(db, doc_id, empresa_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado")


@router.get("/{doc_id}/chunks", response_model=list[ChunkOut])
def list_chunks(
    doc_id: int,
    empresa_id: int = Depends(get_empresa_id),
    db: Session = Depends(get_db),
) -> list[ChunkOut]:
    """Chunks de un documento, para inspeccionar el troceo."""
    if service.get_document(db, doc_id, empresa_id) is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return [ChunkOut.model_validate(c) for c in service.list_chunks(db, doc_id)]
