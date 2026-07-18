from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    """Representación de un documento hacia el frontend. No expone `storage_ref`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo: str
    estado: str
    fecha_subida: datetime


class ChunkOut(BaseModel):
    """Un chunk hacia el frontend (para inspeccionar el troceo)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    page_start: int | None
    page_end: int | None
    section: str | None
    chunk_index: int
    texto: str


class SearchQuery(BaseModel):
    """Petición de búsqueda."""

    query: str


class SearchResultOut(BaseModel):
    """Un chunk recuperado con su traza de scoring."""

    chunk_id: int
    doc_id: int
    chunk_index: int
    page_start: int | None
    page_end: int | None
    texto: str
    rerank_score: float | None
    rrf_score: float
    vector_rank: int | None
    text_rank: int | None
