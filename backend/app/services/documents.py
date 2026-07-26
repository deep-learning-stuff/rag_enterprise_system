"""Lógica de negocio de documentos (Fases 1-3: ingesta + parseo/chunking + embeddings).

Mantiene los endpoints finos: aquí vive el "qué hay que hacer", no en el router.
Los pasos del pipeline (parse, chunk, embed) viven separados y se orquestan aquí.
"""

import io
import logging
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import embedder
from app.ingest.chunker import chunk as chunk_pages
from app.ingest.parser import parse
from app.models.area import Area
from app.models.chunk import Chunk
from app.models.document import Document
from app.storage import storage

logger = logging.getLogger(__name__)


def set_document_areas(
    db: Session, doc: Document, area_ids: list[int], empresa_id: int
) -> None:
    """Reemplaza el conjunto de áreas del documento.

    Exige al menos un área (un documento sin área quedaría huérfano: ningún `usuario`
    podría verlo) y que TODAS pertenezcan a la empresa del documento (si no, sería una
    fuga: asignar un doc al área de otra empresa). No hace commit: lo hace quien llama.
    """
    ids = list(dict.fromkeys(area_ids))  # dedup conservando orden
    if not ids:
        raise ValueError("El documento debe pertenecer al menos a un área.")
    areas = list(
        db.scalars(
            select(Area).where(Area.id.in_(ids), Area.empresa_id == empresa_id)
        )
    )
    if len(areas) != len(ids):
        raise ValueError("Alguna área no existe o no pertenece a la empresa.")
    doc.areas = areas


def create_document(
    db: Session, *, data: BinaryIO, filename: str, empresa_id: int, area_ids: list[int]
) -> Document:
    """Guarda el fichero, registra el documento y lanza el procesado (parse + chunk).

    `empresa_id` sella el documento (y, en cascada, sus chunks) a la empresa dueña.
    `area_ids` son las áreas de acceso del documento (al menos una, de esa empresa).
    """
    ref = storage.save(data, filename=filename)
    tipo = Path(filename).suffix.lstrip(".").lower() or "desconocido"

    doc = Document(
        nombre=filename, tipo=tipo, estado="subido", storage_ref=ref, empresa_id=empresa_id
    )
    db.add(doc)
    db.flush()  # asigna doc.id sin cerrar la transacción, para colgar las áreas
    set_document_areas(db, doc, area_ids, empresa_id)
    db.commit()
    db.refresh(doc)

    process_document(db, doc)
    return doc


def create_document_from_text(
    db: Session, *, texto: str, nombre: str, empresa_id: int, area_ids: list[int]
) -> Document:
    """Crea un documento a partir de texto en memoria (Markdown de un borrador de gap).

    Mismo camino que `create_document`, pero la fuente es una cadena en vez de un fichero
    subido: se envuelve en un buffer binario y pasa por el pipeline normal (parse ->
    chunk -> embed). Se guarda como `.md` para que el parser lo trate como texto.
    """
    filename = nombre if nombre.lower().endswith(".md") else f"{nombre}.md"
    buffer = io.BytesIO(texto.encode("utf-8"))
    return create_document(
        db, data=buffer, filename=filename, empresa_id=empresa_id, area_ids=area_ids
    )


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
                empresa_id=doc.empresa_id,  # el chunk hereda la empresa de su documento
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


def list_documents(db: Session, empresa_id: int) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.empresa_id == empresa_id)
            .order_by(Document.fecha_subida.desc())
        )
    )


def get_document(db: Session, doc_id: int, empresa_id: int) -> Document | None:
    """Documento por id, SOLO si es de la empresa (aislamiento por tenant).

    Si es de otra empresa devuelve None (el router responde 404, sin filtrar existencia).
    """
    doc = db.get(Document, doc_id)
    if doc is None or doc.empresa_id != empresa_id:
        return None
    return doc


def list_chunks(db: Session, doc_id: int) -> list[Chunk]:
    return list(
        db.scalars(
            select(Chunk).where(Chunk.doc_id == doc_id).order_by(Chunk.chunk_index)
        )
    )


def delete_document(db: Session, doc_id: int, empresa_id: int) -> bool:
    """Borra un documento (subido por error) y su fichero. Devuelve False si no existe.

    Solo de la propia empresa (aislamiento). En BD el borrado arrastra por FK: los chunks
    (ondelete CASCADE) y los vínculos documento-área; los gaps que apuntaban a este
    documento quedan con la referencia a NULL (ondelete SET NULL), no se rompen. El
    fichero se borra DESPUÉS de confirmar el borrado en BD: si algo fallara, no dejamos
    una fila apuntando a un fichero inexistente (a lo sumo un fichero huérfano).
    """
    doc = get_document(db, doc_id, empresa_id)
    if doc is None:
        return False
    ref = doc.storage_ref
    db.delete(doc)
    db.commit()
    storage.delete(ref)
    return True
