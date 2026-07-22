# Importa aquí cada modelo para que quede registrado en Base.metadata
# (Alembic lo necesita para autogenerar migraciones).
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.gap import Gap
from app.models.query_log import QueryLog

__all__ = ["Chunk", "Document", "Gap", "QueryLog"]
