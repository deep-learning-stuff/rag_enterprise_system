"""Generación de embeddings.

El pipeline usa la instancia `embedder` (interfaz `Embedder`) sin acoplarse a cómo se
sirve el modelo. Hoy es TEI por HTTP; cambiar de serving es cambiar solo esta línea.
"""
from app.config import settings
from app.embeddings.base import Embedder
from app.embeddings.tei import TEIEmbedder

embedder: Embedder = TEIEmbedder(settings.embeddings_url)

__all__ = ["Embedder", "embedder"]
