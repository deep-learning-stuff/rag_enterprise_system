from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.area import Area, documento_area


class Document(Base):
    """Documento subido.

    Esqueleto de ejemplo: SOLO metadatos, para probar el flujo modelo -> migración.
    Nada de chunks ni embeddings todavía (eso vive en la skill rag-conventions).
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Empresa (tenant) dueña del documento. La sella la ingesta. Ver modelo Empresa.
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(50))
    estado: Mapped[str] = mapped_column(String(32), default="subido")
    # Referencia opaca al fichero en el almacenamiento (ver app.storage). No es una ruta.
    storage_ref: Mapped[str] = mapped_column(String(512))
    fecha_subida: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Áreas a las que pertenece el documento (N:M). `selectin` para cargarlas de golpe
    # y evitar N+1 y accesos a relación sobre objetos "detached" tras el commit.
    areas: Mapped[list[Area]] = relationship(
        secondary=documento_area, lazy="selectin"
    )

    @property
    def area_ids(self) -> list[int]:
        """Ids de las áreas del documento (para exponer en `DocumentOut`)."""
        return [a.id for a in self.areas]
