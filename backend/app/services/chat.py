"""Chat persistente (Fase C): conversaciones con seguimientos contextualizados.

Orquesta el turno de chat SIN romper el invariante grounded: el historial solo sirve
para reescribir el seguimiento a una consulta autónoma; la respuesta se genera con los
chunks recuperados (reutiliza `answer_query`), nunca con el historial. Así "¿y en 2023?"
se convierte en una pregunta completa, se recupera sobre ella y se responde con documentos.

La contextualización es HEURÍSTICA: solo se reescribe (llamada barata al LLM, sin chunks)
cuando el mensaje parece depender del contexto; si es autónomo, se recupera tal cual.
"""

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.generation import Turno, generator
from app.models.conversacion import Conversacion
from app.models.mensaje import Mensaje
from app.retrieval.search import Candidate
from app.services.answers import AnswerData, answer_query

# Cuántos turnos recientes se le pasan al reescritor (acota el prompt y el coste).
_MAX_TURNOS_HISTORIAL = 6

# Determinantes/pronombres que delatan una referencia al contexto anterior. Conjunto
# ajustado a anáforas fuertes: un falso positivo solo cuesta una reescritura de más
# (inocua: si ya era autónoma, el modelo la devuelve igual).
_DEICTICOS = {
    "eso", "esa", "ese", "esos", "esas", "esto", "esta", "este", "estos", "estas",
    "aquello", "aquel", "aquella", "aquellos", "aquellas", "ahi", "ahí", "alli", "allí",
    "anterior", "dicho", "dicha", "mencionado", "mencionada",
}
_CONECTORES_INICIO = ("y ", "o ", "pero ", "entonces", "además", "ademas", "también", "tambien")


def _titulo(texto: str) -> str:
    """Título de la conversación = primera línea del primer mensaje, truncada (sin LLM)."""
    linea = next((l for l in texto.strip().splitlines() if l.strip()), "Nueva conversación")
    linea = linea.strip()
    return linea[:80].rstrip() + ("…" if len(linea) > 80 else "")


def _parece_dependiente(mensaje: str) -> bool:
    """Heurística: ¿el mensaje parece un seguimiento que depende del contexto?

    Dispara con mensajes muy cortos (elípticos: "¿y en 2023?"), que empiezan por un
    conector ("y...", "pero..."), o con anáforas ("eso", "ese", "el anterior"...). Solo
    decide SI reescribir; la reescritura en sí la hace el LLM.
    """
    m = mensaje.strip().lower()
    if not m:
        return False
    palabras = re.findall(r"\w+", m)
    if len(palabras) <= 4:  # muy corto → probablemente elíptico
        return True
    if m.lstrip("¿¡ ").startswith(_CONECTORES_INICIO):
        return True
    return bool(set(palabras) & _DEICTICOS)


def _cita_dict(c: Candidate) -> dict:
    """Foto de un chunk citado, con el formato que pinta el frontend (SearchResultOut)."""
    return {
        "chunk_id": c.chunk.id,
        "doc_id": c.chunk.doc_id,
        "chunk_index": c.chunk.chunk_index,
        "page_start": c.chunk.page_start,
        "page_end": c.chunk.page_end,
        "texto": c.chunk.texto,
        "rerank_score": c.rerank_score,
        "cosine": c.cosine,
        "rrf_score": c.rrf_score,
        "vector_rank": c.vector_rank,
        "text_rank": c.text_rank,
    }


def listar_conversaciones(
    db: Session, empresa_id: int, usuario_id: int
) -> list[Conversacion]:
    """Conversaciones del usuario (solo las suyas), la más activa primero."""
    return list(
        db.scalars(
            select(Conversacion)
            .where(
                Conversacion.empresa_id == empresa_id,
                Conversacion.usuario_id == usuario_id,
            )
            .order_by(Conversacion.actualizada.desc())
        )
    )


def get_conversacion(
    db: Session, conv_id: int, empresa_id: int, usuario_id: int
) -> Conversacion | None:
    """Conversación por id SOLO si es de este usuario y empresa (si no, None → 404)."""
    conv = db.get(Conversacion, conv_id)
    if conv is None or conv.empresa_id != empresa_id or conv.usuario_id != usuario_id:
        return None
    return conv


def mensajes_de(db: Session, conv_id: int) -> list[Mensaje]:
    return list(
        db.scalars(
            select(Mensaje)
            .where(Mensaje.conversacion_id == conv_id)
            .order_by(Mensaje.id)
        )
    )


def eliminar_conversacion(db: Session, conversacion: Conversacion) -> None:
    db.delete(conversacion)  # CASCADE borra sus mensajes
    db.commit()


def _historial(db: Session, conv_id: int) -> list[Turno]:
    """Últimos turnos con texto (para reescribir el seguimiento)."""
    msgs = mensajes_de(db, conv_id)[-_MAX_TURNOS_HISTORIAL:]
    return [Turno(rol=m.rol, texto=m.texto) for m in msgs if m.texto]


def responder(
    db: Session,
    conversacion: Conversacion,
    texto: str,
    empresa_id: int,
    area_ids: list[int] | None,
) -> tuple[Mensaje, Mensaje]:
    """Procesa un turno: contextualiza el seguimiento, recupera+genera y persiste los dos
    mensajes (usuario y asistente). Devuelve (mensaje_usuario, mensaje_asistente).

    Los mensajes se guardan DESPUÉS de generar: si el LLM falla, no queda un turno a medias
    (el frontend conserva el texto y reintenta).
    """
    historial = _historial(db, conversacion.id)  # turnos previos a este mensaje

    consulta = texto
    if historial and _parece_dependiente(texto):
        consulta = generator.reescribir_consulta(texto, historial)

    data: AnswerData = answer_query(db, consulta, empresa_id, area_ids)

    m_user = Mensaje(
        conversacion_id=conversacion.id,
        rol="usuario",
        texto=texto,
        consulta_resuelta=consulta if consulta != texto else None,
    )
    m_bot = Mensaje(
        conversacion_id=conversacion.id,
        rol="asistente",
        texto=data.answer,
        answered=data.answered,
        reason=data.reason,
        citas=[_cita_dict(c) for c in data.citations],
    )
    db.add_all([m_user, m_bot])
    conversacion.actualizada = datetime.now(timezone.utc)  # sube al tope de la lista
    db.commit()
    db.refresh(m_user)
    db.refresh(m_bot)
    return m_user, m_bot


def crear_conversacion(
    db: Session,
    empresa_id: int,
    usuario_id: int,
    primer_mensaje: str,
    area_ids: list[int] | None,
) -> Conversacion:
    """Crea una conversación (título del primer mensaje) y procesa ese primer turno.

    Si la generación falla, se borra la conversación recién creada para no dejar hilos
    vacíos, y se propaga el error (lo mapea el router a 502/503, como /answer).
    """
    conv = Conversacion(
        empresa_id=empresa_id, usuario_id=usuario_id, titulo=_titulo(primer_mensaje)
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    try:
        responder(db, conv, primer_mensaje, empresa_id, area_ids)
    except Exception:
        db.delete(conv)
        db.commit()
        raise
    return conv
