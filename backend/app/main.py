from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers import documents, search

app = FastAPI(title="RAG interno — esqueleto")

app.include_router(documents.router)
app.include_router(search.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Diagnóstico: confirma que la API responde y que la BD es alcanzable."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}
