from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Sesion(Base):
    """Sesión de servidor: el token opaco vive en una cookie httpOnly del navegador y
    aquí se guarda SOLO su hash (sha256).

    Al ser en servidor, el logout puede borrar la fila y revocar la sesión de verdad
    (a diferencia de un JWT). `expira` fija su caducidad.
    """

    __tablename__ = "sesiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expira: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
