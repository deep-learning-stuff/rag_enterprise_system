from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class QueryLog(Base):
    """Registro de cada consulta a /answer (invariante de CLAUDE.md: toda consulta se
    loguea, con sus chunks recuperados, scores y si se respondió).

    Cuando `answered=False`, `gap_id` enlaza con el gap (grupo de preguntas
    equivalentes, ver `app.models.gap`) al que se sumó esta pregunta.
    """

    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    pregunta: Mapped[str] = mapped_column(Text)
    answered: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gap_id: Mapped[int | None] = mapped_column(
        ForeignKey("gaps.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # [{chunk_id, rerank_score, cosine, rrf_score, citado}, ...] — los candidatos que
    # devolvió hybrid_search (ya filtrados por umbral); vacío si fue abstención directa.
    chunks: Mapped[list] = mapped_column(JSON)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
