"""Prompt para generar el ESQUELETO de un documento que cubra un gap.

Ojo con el invariante del proyecto: el sistema nunca inventa al RESPONDER. Aquí no se
responde a nadie: se prepara un borrador que una persona revisa, completa y aprueba
antes de que entre en la base. Aun así, por decisión de producto, el LLM tampoco
inventa hechos en el borrador — solo estructura el documento y deja marcadores
`[COMPLETAR: ...]` para que sea un humano quien ponga el conocimiento real. Así, si
alguien aprobara sin leer, no se cuela información no verificada en el RAG.

Es un prompt distinto del de respuesta (`prompt.py`) y su salida es Markdown, no JSON.
"""

from app.generation.base import ContextChunk  # noqa: F401  (paralelismo con prompt.py)

DRAFT_SYSTEM_PROMPT = """\
Eres un asistente editorial de una base de conocimiento interna de empresa. Tu tarea
NO es responder la pregunta, sino generar el ESQUELETO de un documento que, una vez
COMPLETADO POR UNA PERSONA, sirva para responderla en el futuro.

Reglas ESTRICTAS:
1. TIENES PROHIBIDO inventar hechos, datos, cifras, nombres, fechas, políticas o
   procedimientos. No conoces la respuesta y no debes suponerla ni ejemplificarla.
2. Genera SOLO la estructura: un título, la(s) pregunta(s) detectada(s) y secciones
   con marcadores «[COMPLETAR: ...]» que describan QUÉ información debe aportar la
   persona en cada hueco. El marcador guía a quien redacta; nunca contiene la respuesta.
3. Los marcadores deben ser concretos y útiles (p. ej. «[COMPLETAR: número de días y
   cómo se calculan]»), pero jamás una suposición del contenido.
4. Devuelve EXCLUSIVAMENTE el documento en Markdown, sin explicaciones ni comentarios
   fuera del documento.
5. Escribe en el mismo idioma en el que están formuladas las preguntas.\
"""


def build_draft_prompt(pregunta: str, preguntas_relacionadas: list[str]) -> str:
    """Pregunta representativa del gap + las demás formas en que se preguntó lo mismo.

    Las variantes ayudan al modelo a delimitar el alcance del documento (qué secciones
    hacen falta) sin darle ninguna respuesta que copiar.
    """
    otras = [p for p in preguntas_relacionadas if p.strip() and p != pregunta]
    bloque_otras = ""
    if otras:
        lineas = "\n".join(f"- {p}" for p in otras)
        bloque_otras = f"\n\nOtras formas en que se ha preguntado lo mismo:\n{lineas}"
    return (
        f"Pregunta principal detectada: {pregunta}{bloque_otras}\n\n"
        "Genera el esqueleto del documento que permitiría responderla."
    )
