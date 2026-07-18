"""Reordenación por relevancia (rerank).

El retrieval usa la instancia `reranker` (interfaz `Reranker`) sin acoplarse al serving.
Hoy es un segundo TEI por HTTP; cambiarlo es cambiar solo esta línea.
"""
from app.config import settings
from app.reranking.base import Reranker
from app.reranking.tei import TEIReranker

reranker: Reranker = TEIReranker(settings.reranker_url)

__all__ = ["Reranker", "reranker"]
