from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Invitacion(Base):
    """Invitación de un solo uso para que un usuario fije su contraseña.

    El token se le entrega al usuario por enlace; aquí se guarda SOLO su hash (sha256),
    nunca el valor en claro. `usada_en` marca cuándo se consumió (una vez usada ya no
    vale); `expira`, hasta cuándo es válida.
    """

    __tablename__ = "invitaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expira: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
