from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db import Base


class Chunk(Base):
    """Trozo de un documento, con la metadata necesaria para citarlo.

    Fase 2: solo texto + metadata. La columna `embedding` (vector) y `tsv` (full-text)
    llegan en la Fase 3, cuando se decida el serving de BGE-M3.
    """

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    texto: Mapped[str] = mapped_column(Text)
    # Rango de páginas que abarca el chunk (iguales si vive en una sola página).
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    # Vector denso de BGE-M3. Nullable: se rellena tras el chunking (estado indexado).
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )
    # Full-text en español, generado por Postgres a partir de `texto` (no se escribe
    # a mano). Se usa para la búsqueda por palabras clave, complementaria a la vectorial.
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed("to_tsvector('spanish', texto)", persisted=True)
    )
