# Importa aquí cada modelo para que quede registrado en Base.metadata
# (Alembic lo necesita para autogenerar migraciones).
from app.models.chunk import Chunk
from app.models.document import Document

__all__ = ["Chunk", "Document"]
