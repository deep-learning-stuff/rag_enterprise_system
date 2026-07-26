from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db import Base


class Gap(Base):
    """Grupo de preguntas sin respuesta que son, en esencia, la misma pregunta.

    El agrupado es incremental (ver app.services.gaps): cada pregunta sin respuesta se
    compara por similitud coseno contra los gaps existentes; si se parece lo bastante a
    uno, se le suma (su embedding se actualiza como media móvil); si no, abre un gap
    nuevo. No hay reclustering por lotes a propósito: un gap es una fila estable en el
    tiempo, porque encima lleva estado editorial (borradores).

    Ciclo editorial (`estado`): `pendiente` (sin borrador) → `borrador` (generado, se
    puede editar) → `ingerido` (el borrador se aprobó y entró como documento nuevo) o
    `descartado` (rechazado). `resuelto` es un cierre distinto: el gap quedó cubierto por
    OTRO documento ya existente (no por su propio borrador). `documento_id` enlaza el gap
    con el documento nacido de su borrador (estado `ingerido`).

    `posible_resuelto` lo pone el re-chequeo manual (ver app.services.gaps.recheck_gaps):
    marca que, con la base ya actualizada, el retrieval de la pregunta del gap vuelve a
    superar el umbral, así que quizá ya esté cubierto. No cierra el gap: un humano lo
    confirma (→ `resuelto`) o lo ignora. `resuelto_por_doc_id` apunta al documento que lo
    cubriría.
    """

    __tablename__ = "gaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Empresa (tenant) dueña del gap. Los gaps se agrupan POR empresa: `find_or_create_gap`
    # solo compara contra gaps de la misma empresa. Ver modelo Empresa.
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"), index=True
    )
    pregunta_representativa: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))
    n_ocurrencias: Mapped[int] = mapped_column(Integer, default=1)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", server_default="pendiente")
    borrador: Mapped[str | None] = mapped_column(Text, nullable=True)
    documento_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    posible_resuelto: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    resuelto_por_doc_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    primera_vez: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ultima_vez: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
