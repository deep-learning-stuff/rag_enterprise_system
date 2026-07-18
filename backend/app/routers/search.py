from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.retrieval.search import hybrid_search
from app.schemas import SearchQuery, SearchResultOut

router = APIRouter(tags=["search"])


@router.post("/search", response_model=list[SearchResultOut])
def search(body: SearchQuery, db: Session = Depends(get_db)) -> list[SearchResultOut]:
    """Recuperación híbrida (vectorial + full-text + RRF). No genera respuesta aún."""
    candidates = hybrid_search(db, body.query)
    return [
        SearchResultOut(
            chunk_id=c.chunk.id,
            doc_id=c.chunk.doc_id,
            chunk_index=c.chunk.chunk_index,
            page_start=c.chunk.page_start,
            page_end=c.chunk.page_end,
            texto=c.chunk.texto,
            rerank_score=c.rerank_score,
            rrf_score=c.rrf_score,
            vector_rank=c.vector_rank,
            text_rank=c.text_rank,
        )
        for c in candidates
    ]
