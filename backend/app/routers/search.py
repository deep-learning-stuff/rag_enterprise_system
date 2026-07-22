import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.generation import GenerationError
from app.retrieval.search import Candidate, hybrid_search
from app.schemas import AnswerOut, SearchQuery, SearchResultOut
from app.services.answers import answer_query

router = APIRouter(tags=["search"])


def _to_result_out(c: Candidate) -> SearchResultOut:
    return SearchResultOut(
        chunk_id=c.chunk.id,
        doc_id=c.chunk.doc_id,
        chunk_index=c.chunk.chunk_index,
        page_start=c.chunk.page_start,
        page_end=c.chunk.page_end,
        texto=c.chunk.texto,
        rerank_score=c.rerank_score,
        cosine=c.cosine,
        rrf_score=c.rrf_score,
        vector_rank=c.vector_rank,
        text_rank=c.text_rank,
    )


@router.post("/search", response_model=list[SearchResultOut])
def search(body: SearchQuery, db: Session = Depends(get_db)) -> list[SearchResultOut]:
    """Recuperación híbrida (vectorial + full-text + RRF). Devuelve candidatos crudos,
    sin generar respuesta: sirve para inspeccionar y afinar el retrieval."""
    return [_to_result_out(c) for c in hybrid_search(db, body.query)]


@router.post("/answer", response_model=AnswerOut)
def answer(body: SearchQuery, db: Session = Depends(get_db)) -> AnswerOut:
    """Respuesta grounded (Fase 5): retrieval → LLM → validación de citas.

    Solo responde con lo que está en los documentos; si no, se abstiene y `reason`
    indica el motivo (ver `AnswerOut`)."""
    try:
        data = answer_query(db, body.query)
    except GenerationError as exc:
        # Configuración incompleta (p.ej. falta la API key): error del despliegue.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        # El proveedor LLM falló o no es alcanzable: error transitorio aguas arriba.
        raise HTTPException(status_code=502, detail=f"proveedor LLM no disponible: {exc}") from exc

    return AnswerOut(
        answered=data.answered,
        answer=data.answer,
        reason=data.reason,
        citations=[_to_result_out(c) for c in data.citations],
    )
