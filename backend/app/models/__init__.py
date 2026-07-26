# Importa aquí cada modelo para que quede registrado en Base.metadata
# (Alembic lo necesita para autogenerar migraciones).
from app.models.area import Area, documento_area, usuario_area
from app.models.chunk import Chunk
from app.models.conversacion import Conversacion
from app.models.document import Document
from app.models.empresa import Empresa
from app.models.gap import Gap
from app.models.invitacion import Invitacion
from app.models.mensaje import Mensaje
from app.models.query_log import QueryLog
from app.models.sesion import Sesion
from app.models.usuario import Usuario

__all__ = [
    "Area",
    "Chunk",
    "Conversacion",
    "Document",
    "Empresa",
    "Gap",
    "Invitacion",
    "Mensaje",
    "QueryLog",
    "Sesion",
    "Usuario",
    "documento_area",
    "usuario_area",
]
