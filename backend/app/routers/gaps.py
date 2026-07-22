from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import GapOut, PreguntaGapOut
from app.services import gaps as service

router = APIRouter(tags=["gaps"])


@router.get("/gaps", response_model=list[GapOut])
def list_gaps(db: Session = Depends(get_db)) -> list[GapOut]:
    """Gaps (preguntas sin respuesta, agrupadas), el más preguntado primero."""
    gaps = service.list_gaps(db)
    preguntas_por_gap = service.list_preguntas_por_gap(db)
    return [
        GapOut(
            id=g.id,
            pregunta_representativa=g.pregunta_representativa,
            n_ocurrencias=g.n_ocurrencias,
            primera_vez=g.primera_vez,
            ultima_vez=g.ultima_vez,
            preguntas=[
                PreguntaGapOut(id=log.id, pregunta=log.pregunta, fecha=log.fecha)
                for log in preguntas_por_gap.get(g.id, [])
            ],
        )
        for g in gaps
    ]
