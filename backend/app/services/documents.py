"""Lógica de negocio de documentos (Fases 1-3: ingesta + parseo/chunking + embeddings).

Mantiene los endpoints finos: aquí vive el "qué hay que hacer", no en el router.
Los pasos del pipeline (parse, chunk, embed) viven separados y se orquestan aquí.
"""

import logging
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import embedder
from app.ingest.chunker import chunk as chunk_pages
from app.ingest.parser import parse
from app.models.chunk import Chunk
from app.models.document import Document
from app.storage import storage

logger = logging.getLogger(__name__)


def create_document(db: Session, *, data: BinaryIO, filename: str) -> Document:
    """Guarda el fichero, registra el documento y lanza el procesado (parse + chunk)."""
    ref = storage.save(data, filename=filename)
    tipo = Path(filename).suffix.lstrip(".").lower() or "desconocido"

    doc = Document(nombre=filename, tipo=tipo, estado="subido", storage_ref=ref)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    process_document(db, doc)
    return doc


def process_document(db: Session, doc: Document) -> None:
    """Pipeline: parsear -> chunkear -> embeber. Avanza el estado del documento.

    Si algo falla, el documento queda en estado `error` (no se propaga la excepción:
    la subida en sí fue correcta, solo falló el procesado).
    """
    try:
        with storage.open(doc.storage_ref) as f:
            pages = parse(f, doc.tipo)
        doc.estado = "parseado"
        db.commit()

        chunks = chunk_pages(pages)
        rows = [
            Chunk(
                doc_id=doc.id,
                texto=c.texto,
                page_start=c.page_start,
                page_end=c.page_end,
                section=c.section,
                chunk_index=c.chunk_index,
            )
            for c in chunks
        ]
        db.add_all(rows)
        doc.estado = "chunkeado"
        db.commit()

        # Embeddings: un vector por chunk (BGE-M3 vía TEI). estado -> indexado.
        if rows:
            vectors = embedder.embed([r.texto for r in rows])
            for row, vector in zip(rows, vectors):
                row.embedding = vector
        doc.estado = "indexado"
        db.commit()
    except Exception:
        logger.exception("Fallo procesando el documento %s", doc.id)
        db.rollback()
        doc.estado = "error"
        db.commit()


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.fecha_subida.desc())))


def get_document(db: Session, doc_id: int) -> Document | None:
    return db.get(Document, doc_id)


def list_chunks(db: Session, doc_id: int) -> list[Chunk]:
    return list(
        db.scalars(
            select(Chunk).where(Chunk.doc_id == doc_id).order_by(Chunk.chunk_index)
        )
    )
