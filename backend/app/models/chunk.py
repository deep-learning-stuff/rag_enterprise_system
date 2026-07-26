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
    # Empresa (tenant), denormalizada desde el documento: así el retrieval filtra por
    # empresa sin JOIN y el índice puede pre-filtrar. La hereda del documento en la
    # ingesta. Ver modelo Empresa.
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"), index=True
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
    # Se indexa con DOS configuraciones a la vez: `spanish` aporta la coincidencia entre
    # singular y plural, y `spanish_unaccent` (migración 0006) la tolerancia a las
    # tildes. Cada una rompe casos que la otra cubre, de ahí la unión. La consulta debe
    # combinar las dos igual (ver retrieval/search.py) o no encontrará la mitad.
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('spanish', texto) || to_tsvector('spanish_unaccent', texto)",
            persisted=True,
        ),
    )
