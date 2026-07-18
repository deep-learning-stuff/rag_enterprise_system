from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Document(Base):
    """Documento subido.

    Esqueleto de ejemplo: SOLO metadatos, para probar el flujo modelo -> migración.
    Nada de chunks ni embeddings todavía (eso vive en la skill rag-conventions).
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(50))
    estado: Mapped[str] = mapped_column(String(32), default="subido")
    # Referencia opaca al fichero en el almacenamiento (ver app.storage). No es una ruta.
    storage_ref: Mapped[str] = mapped_column(String(512))
    fecha_subida: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
